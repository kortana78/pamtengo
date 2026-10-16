from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.agents.providers import provider_status
from app.agents.workflow import run_qualify_and_draft
from app.core.auth import get_current_user_email
from app.core.config import settings
from app.db.session import get_db
from app.models.entities import (
    Activity,
    AgentRun,
    AgentStep,
    Company,
    IdealCustomerProfile,
    Lead,
    OutreachDraft,
)
from app.schemas.api import (
    ActivityOut,
    AgentRunOut,
    AgentStepOut,
    CompanyCreate,
    CompanyOut,
    DraftUpdate,
    ICPCreate,
    ICPOut,
    LeadCreate,
    LeadListItem,
    LeadUpdate,
    OutreachDraftOut,
    SimulateSendIn,
)
from app.services import email_mock
from app.services.csv_import import parse_csv
from app.services.safety import contains_prompt_injection, sanitize_csv_cell
from app.services.scoring import default_icp

router = APIRouter()


def _lead_item(lead: Lead) -> LeadListItem:
    co: Company | None = lead.company
    return LeadListItem(
        id=lead.id,
        company_id=lead.company_id,
        full_name=lead.full_name,
        job_title=lead.job_title,
        email=lead.email,
        status=lead.status,
        source=lead.source,
        fit_score=lead.fit_score,
        fit_explanation=lead.fit_explanation,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
        company_name=co.name if co else None,
        company_country=co.country if co else None,
        company_industry=co.industry if co else None,
    )


def _log(
    db: Session, lead_id: str, activity_type: str, description: str, meta: dict | None = None
) -> None:
    db.add(
        Activity(
            lead_id=lead_id, activity_type=activity_type, description=description, meta=meta or {}
        )
    )


# ---------- companies ----------
@router.get("/companies")
def list_companies(
    db: Session = Depends(get_db),
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = db.query(Company)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(Company.name.ilike(like), Company.industry.ilike(like), Company.country.ilike(like))
        )
    total = query.count()
    items = (
        query.order_by(Company.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [CompanyOut.model_validate(c).model_dump(mode="json") for c in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/companies", status_code=201)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    co = Company(**payload.model_dump())
    db.add(co)
    db.commit()
    db.refresh(co)
    return CompanyOut.model_validate(co).model_dump(mode="json")


# ---------- leads ----------
@router.get("/leads")
def list_leads(
    db: Session = Depends(get_db),
    q: str | None = None,
    status: str | None = None,
    country: str | None = None,
    industry: str | None = None,
    min_score: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = db.query(Lead).join(Company, Lead.company_id == Company.id)
    if status:
        query = query.filter(Lead.status == status)
    if country:
        query = query.filter(Company.country.ilike(country))
    if industry:
        query = query.filter(Company.industry.ilike(industry))
    if min_score is not None:
        query = query.filter(Lead.fit_score >= min_score)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(Lead.full_name.ilike(like), Lead.email.ilike(like), Company.name.ilike(like))
        )
    total = query.count()
    leads = (
        query.order_by(Lead.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )
    return {
        "items": [_lead_item(ld).model_dump(mode="json") for ld in leads],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/leads", status_code=201)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)):
    if payload.company_id:
        company = db.get(Company, payload.company_id)
        if company is None:
            raise HTTPException(404, "Company not found")
    else:
        if not payload.company_name:
            raise HTTPException(422, "company_id or company_name is required")
        company = Company(
            name=payload.company_name,
            country=payload.company_country,
            industry=payload.company_industry,
            source=payload.source or "manual",
        )
        db.add(company)
        db.flush()
    existing = (
        db.query(Lead).filter(Lead.email == payload.email, Lead.company_id == company.id).first()
    )
    if existing:
        raise HTTPException(409, "A lead with this email already exists for the company")
    lead = Lead(
        company_id=company.id,
        full_name=payload.full_name,
        job_title=payload.job_title,
        email=str(payload.email),
        source=payload.source or "manual",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    _log(db, lead.id, "lead_created", f"Lead {lead.full_name} created.", {"company": company.name})
    db.commit()
    return _lead_item(lead).model_dump(mode="json")


@router.get("/leads/{lead_id}")
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(404, "Lead not found")
    company = db.get(Company, lead.company_id)
    drafts = (
        db.query(OutreachDraft)
        .filter(OutreachDraft.lead_id == lead_id)
        .order_by(OutreachDraft.created_at.desc())
        .all()
    )
    runs = (
        db.query(AgentRun)
        .filter(AgentRun.lead_id == lead_id)
        .order_by(AgentRun.started_at.desc())
        .all()
    )
    return {
        "lead": _lead_item(lead).model_dump(mode="json"),
        "company": CompanyOut.model_validate(company).model_dump(mode="json") if company else None,
        "drafts": [OutreachDraftOut.model_validate(d).model_dump(mode="json") for d in drafts],
        "agent_runs": [AgentRunOut.model_validate(r).model_dump(mode="json") for r in runs],
    }


@router.patch("/leads/{lead_id}")
def update_lead(lead_id: str, payload: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(404, "Lead not found")
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] is not None:
        data["email"] = str(data["email"])
    for k, v in data.items():
        setattr(lead, k, v)
    db.commit()
    db.refresh(lead)
    _log(db, lead.id, "lead_updated", f"Lead updated: {', '.join(data.keys())}.", {})
    db.commit()
    return _lead_item(lead).model_dump(mode="json")


@router.post("/leads/import")
async def import_leads(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        rows, errors = parse_csv(content)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    created = 0
    skipped_duplicates = 0
    company_cache: dict[str, Company] = {}
    for row in rows:
        cname = row.get("company_name", "").strip()
        email = row.get("email", "").strip().lower()
        company = company_cache.get(cname.lower())
        if company is None:
            company = db.query(Company).filter(func.lower(Company.name) == cname.lower()).first()
            if company is None:
                company = Company(
                    name=cname,
                    country=row.get("company_country") or None,
                    industry=row.get("company_industry") or None,
                    employee_range=row.get("company_size") or None,
                    description=row.get("description") or None,
                    source=row.get("source") or "csv_import",
                )
                db.add(company)
                db.flush()
            company_cache[cname.lower()] = company
        dupe = db.query(Lead).filter(Lead.email == email, Lead.company_id == company.id).first()
        if dupe:
            skipped_duplicates += 1
            continue
        lead = Lead(
            company_id=company.id,
            full_name=row.get("full_name", ""),
            job_title=row.get("job_title") or None,
            email=email,
            source=row.get("source") or "csv_import",
        )
        db.add(lead)
        db.flush()
        created += 1
        if contains_prompt_injection(row.get("description")):
            _log(
                db,
                lead.id,
                "security_flag",
                "Imported description contained instruction-like text; treated as data only.",
                {"quarantined": True},
            )
    db.commit()
    return {"created": created, "skipped_duplicates": skipped_duplicates, "errors": errors}


# ---------- qualify + draft ----------
@router.post("/leads/{lead_id}/qualify", status_code=202)
async def qualify_lead(lead_id: str, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(404, "Lead not found")
    run = AgentRun(
        lead_id=lead_id,
        workflow_type="qualify_and_draft",
        status="running",
        input_snapshot={"lead_id": lead_id},
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    # Execute bounded workflow inline (mock provider is fast; live provider bounded by timeout)
    await run_qualify_and_draft(db, lead_id=lead_id, run=run)
    db.refresh(run)
    _log(
        db,
        lead_id,
        "agent_run",
        f"Qualification workflow {run.status}.",
        {"run_id": run.id, "status": run.status},
    )
    db.commit()
    if run.status == "failed":
        raise HTTPException(500, f"Agent workflow failed: {run.error_message}")
    return AgentRunOut.model_validate(run).model_dump(mode="json")


@router.post("/leads/{lead_id}/draft-outreach", status_code=202)
async def draft_outreach(lead_id: str, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(404, "Lead not found")
    run = AgentRun(
        lead_id=lead_id,
        workflow_type="qualify_and_draft",
        status="running",
        input_snapshot={"lead_id": lead_id, "trigger": "draft-outreach"},
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    await run_qualify_and_draft(db, lead_id=lead_id, run=run)
    db.refresh(run)
    _log(
        db,
        lead_id,
        "agent_run",
        f"Outreach draft workflow {run.status}.",
        {"run_id": run.id, "status": run.status},
    )
    db.commit()
    if run.status == "failed":
        raise HTTPException(500, f"Agent workflow failed: {run.error_message}")
    drafts = db.query(OutreachDraft).filter(OutreachDraft.agent_run_id == run.id).all()
    return {
        "run": AgentRunOut.model_validate(run).model_dump(mode="json"),
        "drafts": [OutreachDraftOut.model_validate(d).model_dump(mode="json") for d in drafts],
    }


# ---------- agent runs ----------
@router.get("/agent-runs")
def list_runs(
    db: Session = Depends(get_db),
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = db.query(AgentRun)
    if status:
        query = query.filter(AgentRun.status == status)
    total = query.count()
    runs = (
        query.order_by(AgentRun.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [AgentRunOut.model_validate(r).model_dump(mode="json") for r in runs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/agent-runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(404, "Agent run not found")
    return AgentRunOut.model_validate(run).model_dump(mode="json")


@router.get("/agent-runs/{run_id}/steps")
def get_run_steps(run_id: str, db: Session = Depends(get_db)):
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(404, "Agent run not found")
    steps = (
        db.query(AgentStep)
        .filter(AgentStep.agent_run_id == run_id)
        .order_by(AgentStep.created_at)
        .all()
    )
    return [AgentStepOut.model_validate(s).model_dump(mode="json") for s in steps]


# ---------- activities / drafts / analytics ----------
@router.get("/leads/{lead_id}/activities")
def lead_activities(lead_id: str, db: Session = Depends(get_db)):
    if db.get(Lead, lead_id) is None:
        raise HTTPException(404, "Lead not found")
    acts = (
        db.query(Activity)
        .filter(Activity.lead_id == lead_id)
        .order_by(Activity.created_at.desc())
        .all()
    )
    return [ActivityOut.model_validate(a).model_dump(mode="json") for a in acts]


@router.get("/outreach-drafts")
def list_drafts(
    db: Session = Depends(get_db),
    status: str | None = None,
    lead_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = db.query(OutreachDraft)
    if status:
        query = query.filter(OutreachDraft.status == status)
    if lead_id:
        query = query.filter(OutreachDraft.lead_id == lead_id)
    total = query.count()
    drafts = (
        query.order_by(OutreachDraft.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [OutreachDraftOut.model_validate(d).model_dump(mode="json") for d in drafts],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.patch("/outreach-drafts/{draft_id}")
def edit_draft(draft_id: str, payload: DraftUpdate, db: Session = Depends(get_db)):
    draft = db.get(OutreachDraft, draft_id)
    if draft is None:
        raise HTTPException(404, "Draft not found")
    if draft.status == "sent":
        raise HTTPException(409, "Sent drafts cannot be edited")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(draft, k, v)
    draft.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(draft)
    _log(
        db,
        draft.lead_id,
        "draft_edited",
        f"Draft {draft.id} edited by user.",
        {"draft_id": draft.id},
    )
    db.commit()
    return OutreachDraftOut.model_validate(draft).model_dump(mode="json")


@router.post("/outreach-drafts/{draft_id}/approve")
def approve_draft(
    draft_id: str, db: Session = Depends(get_db), user_email: str = Depends(get_current_user_email)
):
    draft = db.get(OutreachDraft, draft_id)
    if draft is None:
        raise HTTPException(404, "Draft not found")
    if draft.status == "sent":
        raise HTTPException(409, "Already sent; cannot approve")
    # Allow re-approval of rejected->approved? Only draft/rejected can move to approved.
    if draft.status not in ("draft", "rejected"):
        raise HTTPException(409, f"Cannot approve draft in status '{draft.status}'")
    draft.status = "approved"
    draft.approved_by = user_email  # server-set from auth header; clients cannot set it
    draft.approved_at = datetime.now(UTC)
    db.commit()
    db.refresh(draft)
    _log(
        db,
        draft.lead_id,
        "draft_approved",
        f"Draft approved by {user_email}.",
        {"draft_id": draft.id},
    )
    db.commit()
    return OutreachDraftOut.model_validate(draft).model_dump(mode="json")


@router.post("/outreach-drafts/{draft_id}/reject")
def reject_draft(
    draft_id: str, db: Session = Depends(get_db), user_email: str = Depends(get_current_user_email)
):
    draft = db.get(OutreachDraft, draft_id)
    if draft is None:
        raise HTTPException(404, "Draft not found")
    if draft.status == "sent":
        raise HTTPException(409, "Already sent; cannot reject")
    draft.status = "rejected"
    db.commit()
    db.refresh(draft)
    _log(
        db,
        draft.lead_id,
        "draft_rejected",
        f"Draft rejected by {user_email}.",
        {"draft_id": draft.id},
    )
    db.commit()
    return OutreachDraftOut.model_validate(draft).model_dump(mode="json")


@router.post("/outreach-drafts/{draft_id}/simulate-send")
def simulate_send(
    draft_id: str,
    payload: SimulateSendIn,
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
):
    draft = db.get(OutreachDraft, draft_id)
    if draft is None:
        raise HTTPException(404, "Draft not found")
    if not payload.confirm:
        raise HTTPException(400, 'Explicit confirmation required: send {"confirm": true}.')
    if draft.status != "approved":
        raise HTTPException(409, "Only approved drafts can be (mock) sent. Approve first.")
    # Idempotency: already-sent draft returns the original record without duplicating.
    if draft.status == "approved" and draft.sent_at is not None:
        pass  # fall through to mock provider dedupe
    lead = db.get(Lead, draft.lead_id)
    key = payload.idempotency_key or f"draft:{draft.id}"
    # If this key was used before for this draft, return idempotent result.
    if draft.idempotency_key and draft.idempotency_key == key and draft.sent_at:
        return {"status": "already_sent", "sent_at": draft.sent_at.isoformat(), "duplicate": True}
    result = email_mock.simulate_send(
        draft_id=draft.id,
        to_email=lead.email if lead else "unknown",
        subject=draft.subject,
        idempotency_key=key,
    )
    if not result.get("duplicate"):
        draft.status = "sent"
        draft.sent_at = datetime.now(UTC)
        draft.idempotency_key = key
        if lead:
            lead.status = "contacted"
        db.commit()
        _log(
            db,
            draft.lead_id,
            "mock_send",
            f"Mock email to {lead.email if lead else 'unknown'} by {user_email}. No real delivery.",
            {"draft_id": draft.id, "idempotency_key": key},
        )
        db.commit()
    db.refresh(draft)
    return {
        "status": "sent",
        "draft": OutreachDraftOut.model_validate(draft).model_dump(mode="json"),
        "provider": result,
        "duplicate": result.get("duplicate", False),
    }


@router.get("/analytics/overview")
def analytics_overview(db: Session = Depends(get_db)):
    total = db.query(func.count(Lead.id)).scalar() or 0
    qualified = db.query(func.count(Lead.id)).filter(Lead.status == "qualified").scalar() or 0
    awaiting = (
        db.query(func.count(OutreachDraft.id)).filter(OutreachDraft.status == "draft").scalar() or 0
    )
    sent = (
        db.query(func.count(OutreachDraft.id)).filter(OutreachDraft.status == "sent").scalar() or 0
    )
    recent_runs = db.query(AgentRun).order_by(AgentRun.started_at.desc()).limit(5).all()
    by_status = db.query(Lead.status, func.count(Lead.id)).group_by(Lead.status).all()
    by_country = (
        db.query(Company.country, func.count(Lead.id))
        .join(Lead, Lead.company_id == Company.id)
        .group_by(Company.country)
        .limit(10)
        .all()
    )
    return {
        "total_leads": total,
        "qualified_leads": qualified,
        "drafts_awaiting_approval": awaiting,
        "emails_mock_sent": sent,
        "leads_by_status": [{"status": s, "count": c} for s, c in by_status],
        "leads_by_country": [{"country": c or "Unknown", "count": n} for c, n in by_country],
        "recent_runs": [AgentRunOut.model_validate(r).model_dump(mode="json") for r in recent_runs],
        "how_calculated": (
            "total_leads = COUNT(leads); qualified_leads = COUNT(leads WHERE status='qualified') "
            "(set by the deterministic scoring workflow, score>=60); drafts_awaiting_approval = "
            "COUNT(outreach_drafts WHERE status='draft'); emails_mock_sent = COUNT(drafts WHERE "
            "status='sent') via the mock provider (no real email is ever delivered)."
        ),
    }


@router.get("/leads/export")
def export_leads(db: Session = Depends(get_db)):
    import csv as csvmod
    import io as iom

    from fastapi.responses import PlainTextResponse

    leads = db.query(Lead).join(Company, Lead.company_id == Company.id).limit(5000).all()
    buf = iom.StringIO()
    w = csvmod.writer(buf)
    w.writerow(
        ["full_name", "email", "job_title", "status", "fit_score", "company", "country", "industry"]
    )
    for ld in leads:
        co = ld.company
        w.writerow(
            [
                sanitize_csv_cell(ld.full_name),
                sanitize_csv_cell(ld.email),
                sanitize_csv_cell(ld.job_title or ""),
                ld.status,
                ld.fit_score or "",
                sanitize_csv_cell(co.name if co else ""),
                sanitize_csv_cell(co.country if co and co.country else ""),
                sanitize_csv_cell(co.industry if co and co.industry else ""),
            ]
        )
    return PlainTextResponse(buf.getvalue(), media_type="text/csv")


# ---------- ICP + provider status ----------
@router.get("/icp")
def list_icp(db: Session = Depends(get_db)):
    profiles = db.query(IdealCustomerProfile).order_by(IdealCustomerProfile.created_at.desc()).all()
    if not profiles:
        d = default_icp()
        return [{"id": "default", **d, "created_at": None}]
    return [ICPOut.model_validate(p).model_dump(mode="json") for p in profiles]


@router.post("/icp", status_code=201)
def create_icp(payload: ICPCreate, db: Session = Depends(get_db)):
    profile = IdealCustomerProfile(**payload.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return ICPOut.model_validate(profile).model_dump(mode="json")


@router.get("/ai/status")
def ai_status():
    return {
        **provider_status(),
        "csv_max_bytes": settings.csv_max_bytes,
        "csv_max_rows": settings.csv_max_rows,
    }
