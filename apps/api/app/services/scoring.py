"""Deterministic lead scoring baseline.

Design choice (why deterministic): the fit score must be reproducible,
auditable, and explainable to a sales user. An LLM is good at *explaining*
a result in prose, but its numeric output varies run to run and cannot be
treated as a probability of conversion. The LLM therefore explains the
rule-based result but never overrides it.
"""

from app.schemas.api import CriterionScore, QualificationResult

CRITERIA_WEIGHTS = {
    "industry_relevance": 25.0,
    "country_fit": 20.0,
    "company_size": 15.0,
    "icp_match": 20.0,
    "evidence_completeness": 20.0,
}

SIZE_ORDER = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]


def _norm(values: list[str] | None) -> list[str]:
    return [str(v).strip().lower() for v in (values or []) if str(v).strip()]


def score_lead(
    *,
    company_industry: str | None,
    company_country: str | None,
    employee_range: str | None,
    job_title: str | None,
    email: str | None,
    description: str | None,
    icp_industries: list[str],
    icp_countries: list[str],
    icp_sizes: list[str],
) -> QualificationResult:
    breakdown: list[CriterionScore] = []
    evidence: list[str] = []
    missing: list[str] = []

    # 1. Industry relevance
    ind = (company_industry or "").strip().lower()
    targets_ind = _norm(icp_industries)
    if not ind:
        breakdown.append(
            CriterionScore(
                criterion="industry_relevance",
                points=CRITERIA_WEIGHTS["industry_relevance"] * 0.4,
                max_points=CRITERIA_WEIGHTS["industry_relevance"],
                outcome="unknown",
                note="Company industry is unknown.",
            )
        )
        missing.append("company.industry")
    elif not targets_ind or ind in targets_ind:
        breakdown.append(
            CriterionScore(
                criterion="industry_relevance",
                points=CRITERIA_WEIGHTS["industry_relevance"],
                max_points=CRITERIA_WEIGHTS["industry_relevance"],
                outcome="matched",
                evidence=[f"company.industry={company_industry}"],
                note=f"Industry '{company_industry}' matches target profile.",
            )
        )
        evidence.append(f"company.industry={company_industry}")
    else:
        breakdown.append(
            CriterionScore(
                criterion="industry_relevance",
                points=0,
                max_points=CRITERIA_WEIGHTS["industry_relevance"],
                outcome="mismatched",
                evidence=[f"company.industry={company_industry}"],
                note=f"Industry '{company_industry}' is outside target {icp_industries}.",
            )
        )
        evidence.append(f"company.industry={company_industry}")

    # 2. Country fit
    ctry = (company_country or "").strip().lower()
    targets_ctry = _norm(icp_countries)
    if not ctry:
        breakdown.append(
            CriterionScore(
                criterion="country_fit",
                points=CRITERIA_WEIGHTS["country_fit"] * 0.4,
                max_points=CRITERIA_WEIGHTS["country_fit"],
                outcome="unknown",
                note="Company country is unknown.",
            )
        )
        missing.append("company.country")
    elif not targets_ctry or ctry in targets_ctry:
        breakdown.append(
            CriterionScore(
                criterion="country_fit",
                points=CRITERIA_WEIGHTS["country_fit"],
                max_points=CRITERIA_WEIGHTS["country_fit"],
                outcome="matched",
                evidence=[f"company.country={company_country}"],
                note=f"Country '{company_country}' is in target markets.",
            )
        )
        evidence.append(f"company.country={company_country}")
    else:
        breakdown.append(
            CriterionScore(
                criterion="country_fit",
                points=0,
                max_points=CRITERIA_WEIGHTS["country_fit"],
                outcome="mismatched",
                evidence=[f"company.country={company_country}"],
                note=f"Country '{company_country}' is outside target {icp_countries}.",
            )
        )
        evidence.append(f"company.country={company_country}")

    # 3. Company size
    size = (employee_range or "").strip()
    pref = [s.strip() for s in (icp_sizes or []) if s.strip()]
    if not size:
        breakdown.append(
            CriterionScore(
                criterion="company_size",
                points=CRITERIA_WEIGHTS["company_size"] * 0.4,
                max_points=CRITERIA_WEIGHTS["company_size"],
                outcome="unknown",
                note="Company size is unknown.",
            )
        )
        missing.append("company.employee_range")
    elif not pref or size in pref:
        breakdown.append(
            CriterionScore(
                criterion="company_size",
                points=CRITERIA_WEIGHTS["company_size"],
                max_points=CRITERIA_WEIGHTS["company_size"],
                outcome="matched",
                evidence=[f"company.employee_range={size}"],
                note=f"Size '{size}' fits preferences.",
            )
        )
        evidence.append(f"company.employee_range={size}")
    else:
        breakdown.append(
            CriterionScore(
                criterion="company_size",
                points=0,
                max_points=CRITERIA_WEIGHTS["company_size"],
                outcome="mismatched",
                evidence=[f"company.employee_range={size}"],
                note=f"Size '{size}' is outside preferences {pref}.",
            )
        )
        evidence.append(f"company.employee_range={size}")

    # 4. ICP match (seniority signal from title + email presence)
    title = (job_title or "").lower()
    senior_terms = ["founder", "ceo", "cto", "director", "head", "manager", "owner", "chief"]
    has_senior = any(t in title for t in senior_terms)
    if not job_title:
        breakdown.append(
            CriterionScore(
                criterion="icp_match",
                points=CRITERIA_WEIGHTS["icp_match"] * 0.4,
                max_points=CRITERIA_WEIGHTS["icp_match"],
                outcome="unknown",
                note="Job title unknown; decision-maker status unclear.",
            )
        )
        missing.append("lead.job_title")
    elif has_senior:
        breakdown.append(
            CriterionScore(
                criterion="icp_match",
                points=CRITERIA_WEIGHTS["icp_match"],
                max_points=CRITERIA_WEIGHTS["icp_match"],
                outcome="matched",
                evidence=[f"lead.job_title={job_title}"],
                note="Contact appears to be a decision-maker.",
            )
        )
        evidence.append(f"lead.job_title={job_title}")
    else:
        breakdown.append(
            CriterionScore(
                criterion="icp_match",
                points=CRITERIA_WEIGHTS["icp_match"] * 0.4,
                max_points=CRITERIA_WEIGHTS["icp_match"],
                outcome="unknown",
                evidence=[f"lead.job_title={job_title}"],
                note="Title does not clearly indicate decision-maker; treat as unknown.",
            )
        )
        evidence.append(f"lead.job_title={job_title}")

    # 5. Evidence completeness
    fields = [company_industry, company_country, employee_range, job_title, email, description]
    filled = sum(1 for f in fields if f and str(f).strip())
    completeness = filled / len(fields)
    pts = round(CRITERIA_WEIGHTS["evidence_completeness"] * completeness, 1)
    breakdown.append(
        CriterionScore(
            criterion="evidence_completeness",
            points=pts,
            max_points=CRITERIA_WEIGHTS["evidence_completeness"],
            outcome="matched"
            if completeness >= 0.8
            else ("unknown" if completeness >= 0.4 else "mismatched"),
            note=f"{filled}/{len(fields)} key fields present.",
        )
    )
    if completeness < 1:
        for name, val in [
            ("company.description", description),
            ("lead.email", email),
        ]:
            if not val:
                missing.append(name)

    total = round(sum(c.points for c in breakdown))
    total = max(0, min(100, total))
    matched = sum(1 for c in breakdown if c.outcome == "matched")
    explanation = (
        f"Score {total}/100: {matched}/5 criteria matched. "
        + " ".join(c.note for c in breakdown)
        + " This is a rule-based fit score, not a probability of conversion."
    )
    return QualificationResult(
        score=total,
        breakdown=breakdown,
        evidence=evidence,
        missing_info=sorted(set(missing)),
        explanation=explanation,
    )


def default_icp() -> dict:
    return {
        "name": "Default AfCFTA SME ICP",
        "target_industries": ["agriculture", "fintech", "logistics", "retail", "manufacturing"],
        "target_countries": [
            "malawi",
            "zambia",
            "kenya",
            "rwanda",
            "ghana",
            "south africa",
            "nigeria",
        ],
        "company_size_preferences": ["11-50", "51-200", "201-500"],
        "qualification_criteria": {"seniority_required": True},
    }
