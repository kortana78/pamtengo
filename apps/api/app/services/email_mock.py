"""Mock email provider: records sends, never delivers real email."""

from datetime import UTC, datetime

SENT_LOG: list[dict] = []


def simulate_send(
    *, draft_id: str, to_email: str, subject: str, idempotency_key: str | None
) -> dict:
    for entry in SENT_LOG:
        if entry["draft_id"] == draft_id:
            return {**entry, "duplicate": True}
        if idempotency_key and entry.get("idempotency_key") == idempotency_key:
            return {**entry, "duplicate": True}
    entry = {
        "draft_id": draft_id,
        "to": to_email,
        "subject": subject,
        "idempotency_key": idempotency_key,
        "sent_at": datetime.now(UTC).isoformat(),
        "provider": "mock",
        "duplicate": False,
    }
    SENT_LOG.append(entry)
    return entry


def reset_mock() -> None:
    SENT_LOG.clear()
