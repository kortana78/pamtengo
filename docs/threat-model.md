# Threat model (MVP)

## Trust boundaries

- **Browser → API:** dev-only header auth (`X-User-Email`). Anyone who can reach the API can claim any
  email. **Do not expose the MVP API to the public internet or load real customer data.**
- **CSV uploads → DB → agent:** imported text is untrusted. It is validated (UTF-8, required columns,
  email format, 1 MB / 1000-row caps), deduplicated, and scanned for instruction-like content
  (`security_flag` activity). The agent receives descriptions as quoted data, never as instructions.
- **Agent → email:** no edge exists. Sends happen only via `POST .../simulate-send` with an
  authenticated user, `confirm: true`, prior `approved` status, and idempotency keys.

## Controls implemented

- Strict Pydantic validation on every write; consistent 4xx envelopes, no stack traces to clients.
- ORM-only DB access (parameterized); Alembic migrations; no raw SQL from clients.
- Secrets via environment only; structured JSON logs redact `api_key`/`authorization`/`password`
  patterns; PII (emails) redacted in the run-detail UI.
- CORS allowlist via `CORS_ORIGINS`; in-memory per-IP rate limiting (120/min default).
- CSV export sanitizes leading `= + - @` to block formula injection.
- Audit trail: `AgentRun` + `AgentStep` + `Activity` rows for qualification, edits, approvals, sends.

## Known gaps (development-only / incomplete)

1. **Authentication is a placeholder.** Replace `X-User-Email` with OIDC/JWT + role checks
   (`admin`/`sales`/`viewer`) before any real deployment. Approval endpoints currently accept any
   well-formed email header.
2. **Rate limiting is in-memory** (single process). Production needs a shared Redis token bucket or
   ingress-level limiting.
3. **No row-level multi-tenancy.** Single-workspace MVP; all data is visible to all users.
4. **Live LLM path is best-effort.** The `openai_compatible` provider is implemented and bounded but
   has not been exercised against a paid endpoint in this environment; mock mode is the verified path.
5. **No backup/secret-rotation story** beyond `DATABASE_URL` env configuration.
