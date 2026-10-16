"""Bounded LangGraph workflow: qualify a lead and draft outreach.

START -> load_context -> validate_evidence -> evaluate_fit -> draft_outreach
      -> validate_claims -> persist -> END

- Only reads approved DB records via the service layer (allowlisted tools).
- Every node records an AgentStep row with duration.
- LLM calls have timeouts + retry limits; failures are persisted, never crash silently.
- Deterministic scoring is authoritative; the LLM only writes the explanation.
"""

import asyncio
import time
from datetime import UTC, datetime
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agents.providers import ProviderTimeoutError, get_provider
from app.core.config import settings
from app.core.logging import log
from app.models.entities import (
    AgentRun,
    AgentStep,
    Company,
    IdealCustomerProfile,
    Lead,
    OutreachDraft,
)
from app.schemas.api import QualificationResult
from app.services.safety import validate_claims
from app.services.scoring import default_icp, score_lead


class FlowState(TypedDict, total=False):
    run_id: str
    lead_id: str
    context: dict[str, Any]
    evidence_ok: bool
    missing: list[str]
    qualification: dict[str, Any]
    draft: dict[str, Any]
    claim_issues: list[str]
    failed: bool
    error: str


def _record_step(
    db: Session, run_id: str, name: str, status: str, inp: str, out: str, ms: int
) -> None:
    db.add(
        AgentStep(
            agent_run_id=run_id,
            step_name=name,
            status=status,
            input_summary=inp[:2000],
            output_summary=out[:2000],
            duration_ms=ms,
        )
    )
    db.commit()


def _node(name: str):
    def deco(fn):
        async def wrapper(state: FlowState, *, db: Session) -> FlowState:
            t0 = time.monotonic()
            try:
                result = await fn(state, db=db)
                ms = int((time.monotonic() - t0) * 1000)
                _record_step(
                    db,
                    state["run_id"],
                    name,
                    "ok",
                    str(state.get("lead_id")),
                    str(result)[:2000],
                    ms,
                )
                if isinstance(result, dict):
                    return {**state, **result}
                return state
            except Exception as e:  # noqa: BLE001 - persisted, then re-raised to fail the run
                ms = int((time.monotonic() - t0) * 1000)
                _record_step(
                    db,
                    state["run_id"],
                    name,
                    "failed",
                    str(state.get("lead_id")),
                    str(e)[:2000],
                    ms,
                )
                log.info(f"workflow node {name} failed: {e}")
                return {**state, "failed": True, "error": f"{name}: {e}"}

        wrapper._node_name = name  # type: ignore[attr-defined]
        return wrapper

    return deco


@_node("load_context")
async def load_context(state: FlowState, *, db: Session) -> dict:
    lead = db.get(Lead, state["lead_id"])
    if lead is None:
        raise ValueError("Lead not found")
    company = db.get(Company, lead.company_id)
    if company is None:
        raise ValueError("Company record missing for lead")
    icp = db.query(IdealCustomerProfile).order_by(IdealCustomerProfile.created_at.desc()).first()
    icp_data = (
        {
            "target_industries": icp.target_industries,
            "target_countries": icp.target_countries,
            "company_size_preferences": icp.company_size_preferences,
        }
        if icp
        else {
            k: v for k, v in default_icp().items() if k != "name" and k != "qualification_criteria"
        }
    )
    if icp is None:
        icp_data = {
            "target_industries": default_icp()["target_industries"],
            "target_countries": default_icp()["target_countries"],
            "company_size_preferences": default_icp()["company_size_preferences"],
        }
    return {
        "context": {
            "lead": {
                "id": lead.id,
                "full_name": lead.full_name,
                "job_title": lead.job_title,
                "email": lead.email,
            },
            "company": {
                "id": company.id,
                "name": company.name,
                "country": company.country,
                "industry": company.industry,
                "employee_range": company.employee_range,
                "description": company.description,
                "website": company.website,
            },
            "icp": icp_data,
        }
    }


@_node("validate_evidence")
async def validate_evidence(state: FlowState, *, db: Session) -> dict:
    ctx = state["context"]
    co, ld = ctx["company"], ctx["lead"]
    missing = [
        label
        for label, val in [
            ("company.name", co.get("name")),
            ("lead.full_name", ld.get("full_name")),
            ("lead.email", ld.get("email")),
        ]
        if not val
    ]
    if missing:
        return {
            "evidence_ok": False,
            "missing": missing,
            "failed": True,
            "error": f"Missing required evidence: {', '.join(missing)}",
        }
    return {"evidence_ok": True, "missing": []}


@_node("evaluate_fit")
async def evaluate_fit(state: FlowState, *, db: Session) -> dict:
    if state.get("failed"):
        return {}
    ctx = state["context"]
    co, ld, icp = ctx["company"], ctx["lead"], ctx["icp"]
    q: QualificationResult = score_lead(
        company_industry=co.get("industry"),
        company_country=co.get("country"),
        employee_range=co.get("employee_range"),
        job_title=ld.get("job_title"),
        email=ld.get("email"),
        description=co.get("description"),
        icp_industries=icp.get("target_industries", []),
        icp_countries=icp.get("target_countries", []),
        icp_sizes=icp.get("company_size_preferences", []),
    )
    provider = get_provider()
    try:
        expl = await asyncio.wait_for(
            provider.explain_qualification(
                lead_name=ld.get("full_name", ""),
                company=co.get("name", ""),
                score=q.score,
                notes=q.explanation,
            ),
            timeout=settings.ai_timeout_seconds,
        )
        status = expl.recommended_status
        summary = expl.summary
    except (TimeoutError, ProviderTimeoutError) as e:
        raise ProviderTimeoutError(f"explain_qualification timed out: {e}") from e
    return {
        "qualification": {
            **q.model_dump(),
            "llm_summary": summary,
            "recommended_status": status,
        }
    }


@_node("draft_outreach")
async def draft_outreach(state: FlowState, *, db: Session) -> dict:
    if state.get("failed"):
        return {}
    ctx = state["context"]
    co, ld = ctx["company"], ctx["lead"]
    q = state.get("qualification", {})
    provider = get_provider()
    last_err: Exception | None = None
    for attempt in range(settings.ai_max_retries + 1):
        try:
            draft = await asyncio.wait_for(
                provider.draft_outreach(
                    lead_name=ld.get("full_name", ""),
                    job_title=ld.get("job_title"),
                    company=co.get("name", ""),
                    industry=co.get("industry"),
                    country=co.get("country"),
                    evidence=q.get("evidence", []),
                ),
                timeout=settings.ai_timeout_seconds,
            )
            return {"draft": draft.model_dump()}
        except (TimeoutError, ProviderTimeoutError):
            last_err = ProviderTimeoutError(f"draft_outreach attempt {attempt + 1} timed out")
            log.info(str(last_err))
            continue
    raise last_err or ProviderTimeoutError("draft_outreach failed without error")


@_node("validate_claims")
async def validate_claims_node(state: FlowState, *, db: Session) -> dict:
    if state.get("failed"):
        return {}
    d = state.get("draft", {})
    safe, issues = validate_claims(d.get("subject", ""), d.get("body", ""), d.get("evidence", []))
    if not safe:
        # Regenerate once with the safe mock template path by stripping risky sentences is
        # out of scope; instead mark for human revision and keep the draft (never auto-send).
        return {"claim_issues": issues}
    return {"claim_issues": []}


@_node("persist")
async def persist(state: FlowState, *, db: Session) -> dict:
    run = db.get(AgentRun, state["run_id"])
    if run is None:
        raise ValueError("AgentRun missing")
    if state.get("failed"):
        run.status = "failed"
        run.error_message = state.get("error", "unknown failure")[:2000]
        run.completed_at = datetime.now(UTC)
        db.commit()
        return {}
    q = state.get("qualification", {})
    d = state.get("draft", {})
    issues = state.get("claim_issues", [])
    # Update lead fit
    lead = db.get(Lead, state["lead_id"])
    if lead is not None:
        lead.fit_score = int(q.get("score", 0))
        lead.fit_explanation = (q.get("llm_summary") or q.get("explanation", ""))[:2000]
        if q.get("recommended_status") in ("qualified", "unqualified"):
            lead.status = q["recommended_status"]
    # Create outreach draft (status draft; approval is a separate human action)
    draft_row = OutreachDraft(
        lead_id=state["lead_id"],
        agent_run_id=state["run_id"],
        subject=d.get("subject", "Follow-up"),
        body=d.get("body", ""),
        evidence=d.get("evidence", [])
        + ([f"claim-warning: {i}" for i in issues] if issues else []),
        status="draft",
    )
    db.add(draft_row)
    db.flush()  # populate draft_row.id before storing it in run.output
    run.status = "completed"
    run.output = {
        "qualification": q,
        "draft_subject": d.get("subject"),
        "claim_issues": issues,
        "draft_id": draft_row.id,
    }
    run.completed_at = datetime.now(UTC)
    db.commit()
    return {"draft_id": draft_row.id}


def build_graph():
    g = StateGraph(FlowState)
    g.add_node("load_context", load_context)
    g.add_node("validate_evidence", validate_evidence)
    g.add_node("evaluate_fit", evaluate_fit)
    g.add_node("draft_outreach", draft_outreach)
    g.add_node("validate_claims", validate_claims_node)
    g.add_node("persist", persist)
    g.set_entry_point("load_context")
    g.add_edge("load_context", "validate_evidence")
    g.add_edge("validate_evidence", "evaluate_fit")
    g.add_edge("evaluate_fit", "draft_outreach")
    g.add_edge("draft_outreach", "validate_claims")
    g.add_edge("validate_claims", "persist")
    g.add_edge("persist", END)
    return g.compile()


async def run_qualify_and_draft(db: Session, *, lead_id: str, run: AgentRun) -> AgentRun:
    """Execute the bounded workflow with DB-bound nodes. Returns the updated run."""
    build_graph()  # validates the transition map; execution below follows the same order.
    node_fns = {
        "load_context": load_context,
        "validate_evidence": validate_evidence,
        "evaluate_fit": evaluate_fit,
        "draft_outreach": draft_outreach,
        "validate_claims": validate_claims_node,
        "persist": persist,
    }
    order = [
        "load_context",
        "validate_evidence",
        "evaluate_fit",
        "draft_outreach",
        "validate_claims",
        "persist",
    ]
    state: FlowState = {"run_id": run.id, "lead_id": lead_id}
    for name in order:
        fn = node_fns[name]
        update = await fn(state, db=db)
        if isinstance(update, dict):
            state = {**state, **update}
        # validate_evidence may set failed=True with missing required info -> still persist failure
        if state.get("failed") and name != "validate_evidence" and name != "persist":
            # jump to persist to record the failure
            persist_update = await node_fns["persist"](state, db=db)
            if isinstance(persist_update, dict):
                state = {**state, **persist_update}
            break
        if state.get("failed") and name == "persist":
            break
    db.refresh(run)
    return run
