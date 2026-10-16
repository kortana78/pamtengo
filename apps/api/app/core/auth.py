"""Dev-only auth. NOT production auth.

The MVP uses a trusted header (X-User-Email) to identify the acting user for
audit purposes (draft approval / activity log). There is no password check here;
deployments must replace this with real authentication (OIDC/JWT) before
handling real customer data. See docs/threat-model.md.
"""

from fastapi import Header, HTTPException

from app.core.logging import redact_email


def get_current_user_email(x_user_email: str | None = Header(default=None)) -> str:
    if not x_user_email or "@" not in x_user_email:
        raise HTTPException(
            status_code=401,
            detail="Authentication required: provide X-User-Email header (dev-only auth).",
        )
    return x_user_email.strip().lower()


def describe_actor(email: str) -> str:
    return redact_email(email) or "unknown"
