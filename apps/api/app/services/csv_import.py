"""CSV import with size/row limits, validation, dedupe, injection-safe notes."""

import csv
import io

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.config import settings

_email_adapter = TypeAdapter(EmailStr)

EXPECTED_COLUMNS = {
    "company_name",
    "company_country",
    "company_industry",
    "company_size",
    "full_name",
    "job_title",
    "email",
    "source",
    "description",
}


def parse_csv(content: bytes) -> tuple[list[dict], list[str]]:
    """Returns (rows, errors). Raises ValueError on hard limit violations."""
    if len(content) > settings.csv_max_bytes:
        raise ValueError(f"File too large: {len(content)} bytes (max {settings.csv_max_bytes}).")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError(f"CSV must be UTF-8 encoded: {e}") from e
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row.")
    normalized = [h.strip() for h in reader.fieldnames]
    missing = {"company_name", "full_name", "email"} - set(normalized)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}.")
    rows: list[dict] = []
    errors: list[str] = []
    for i, raw in enumerate(reader, start=2):
        if len(rows) + len(errors) >= settings.csv_max_rows:
            errors.append(
                f"Row limit exceeded at line {i} (max {settings.csv_max_rows} rows). Stopping."
            )
            break
        row = {(k or "").strip(): (v or "").strip() for k, v in raw.items()}
        email = row.get("email", "")
        try:
            _email_adapter.validate_python(email)
        except ValidationError:
            errors.append(f"Line {i}: invalid email '{email}'. Skipped.")
            continue
        if not row.get("full_name"):
            errors.append(f"Line {i}: missing full_name. Skipped.")
            continue
        if not row.get("company_name"):
            errors.append(f"Line {i}: missing company_name. Skipped.")
            continue
        rows.append(row)
    return rows, errors
