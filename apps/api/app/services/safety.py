"""Claim validation: keep generated content separate from verified evidence."""

import re

FORBIDDEN_PATTERNS = [
    r"i (visited|saw|checked|reviewed|browsed).{0,30}website",
    r"congratulations on.{0,60}(funding|award|launch|expansion)",
    r"your recent (funding|award|launch|expansion)",
    r"we (met|spoke|talked|chatted)( at| last| on)?",
    r"as (we )?discussed",
    r"following up on our (call|meeting|conversation)",
    r"i noticed you (recently|just)",
    r"your (impressive|recent) (growth|achievement|milestone)",
]

PROMPT_INJECTION_MARKERS = [
    "ignore previous instructions",
    "ignore all instructions",
    "system prompt",
    "you are now",
    "disregard the above",
    "jailbreak",
]


def contains_prompt_injection(text: str | None) -> bool:
    if not text:
        return False
    low = text.lower()
    return any(m in low for m in PROMPT_INJECTION_MARKERS)


def validate_claims(subject: str, body: str, evidence: list[str]) -> tuple[bool, list[str]]:
    """Return (safe, issues). Safe drafts cite only supplied evidence."""
    issues: list[str] = []
    combined = f"{subject}\n{body}"
    for pat in FORBIDDEN_PATTERNS:
        if re.search(pat, combined, re.IGNORECASE):
            issues.append(f"Unsupported claim pattern matched: /{pat}/ — no evidence on file.")
    # If body mentions a country/industry fact, it must appear in evidence strings.
    # Lightweight check: flag achievement verbs without evidence citation.
    achievement_verbs = [
        "raised",
        "acquired",
        "launched",
        "won the award",
        "ipo",
        "series a",
        "series b",
    ]
    ev_text = " ".join(evidence).lower()
    for verb in achievement_verbs:
        if verb in combined.lower() and verb not in ev_text:
            issues.append(f"Claim containing '{verb}' has no supporting evidence record.")
    return (len(issues) == 0, issues)


def sanitize_csv_cell(value: str) -> str:
    """Prevent CSV formula injection in exported files."""
    if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value
