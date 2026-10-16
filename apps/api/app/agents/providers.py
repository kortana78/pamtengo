"""LLM provider abstraction.

- MockProvider: deterministic, no network, used for tests/local dev.
- OpenAICompatibleProvider: optional live provider via OpenAI-compatible HTTP API.
Provider is selected with AI_PROVIDER env (mock | openai_compatible).
"""

import asyncio
from typing import Any

import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import log


class StructuredQualification(BaseModel):
    summary: str = Field(max_length=2000)
    recommended_status: str = Field(default="qualified")


class DraftOutput(BaseModel):
    subject: str = Field(max_length=500)
    body: str = Field(max_length=5000)
    evidence: list[str] = []


class ProviderTimeoutError(Exception):
    pass


class ProviderMalformedError(Exception):
    pass


class MockProvider:
    name = "mock"

    async def explain_qualification(
        self, *, lead_name: str, company: str, score: int, notes: str
    ) -> StructuredQualification:
        await asyncio.sleep(0.01)  # simulate latency without network
        return StructuredQualification(
            summary=(
                f"{lead_name} at {company} scored {score}/100 (rule-based fit, not a conversion "
                f"probability). {notes} Missing fields are reported as unknown, not assumed."
            ),
            recommended_status="qualified"
            if score >= 60
            else ("new" if score >= 35 else "unqualified"),
        )

    async def draft_outreach(
        self,
        *,
        lead_name: str,
        job_title: str | None,
        company: str,
        industry: str | None,
        country: str | None,
        evidence: list[str],
    ) -> DraftOutput:
        await asyncio.sleep(0.01)
        role = job_title or "team"
        place = f" in {country}" if country else ""
        sector = f" ({industry})" if industry else ""
        subject = f"Quick idea for {company}{sector}"
        body = (
            f"Hello {lead_name},\n\n"
            "I am writing from Pamtengo, a sales workspace for African markets. "
            f"Based on the information you shared — {company}{sector}{place}, "
            f"role: {role} — I thought our reports could save your team time.\n\n"
            "If it is useful, I can share a one-page fit summary built only "
            "from your public details. "
            "Would a 15-minute call next week work?\n\n"
            "Best regards,\nPamtengo sales team\n\n"
            "P.S. If I got any detail wrong, just reply and I will correct "
            "it — I have not browsed your website."
        )
        return DraftOutput(subject=subject, body=body, evidence=list(evidence))


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(self) -> None:
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url.rstrip("/")
        self.model = settings.openai_model

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=0.5, max=4))
    async def _chat(self, system: str, user: str) -> str:
        timeout = settings.ai_timeout_seconds
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user[: settings.ai_max_tokens * 4]},
                        ],
                        "temperature": 0.2,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except (TimeoutError, httpx.TimeoutException) as e:
            raise ProviderTimeoutError(f"LLM call timed out after {timeout}s") from e

    async def explain_qualification(self, **kwargs: Any) -> StructuredQualification:
        score = kwargs.get("score")
        who = kwargs.get("lead_name")
        company = kwargs.get("company")
        text = await self._chat(
            "Explain a rule-based lead score. Never invent facts. Mark unknowns as unknown.",
            f"Explain score {score} for {who} at {company}: {kwargs.get('notes')}",
        )
        if not text or len(text.strip()) < 5:
            raise ProviderMalformedError("Empty model response")
        score = int(kwargs.get("score", 0))
        return StructuredQualification(
            summary=text[:2000],
            recommended_status="qualified" if score >= 60 else "new",
        )

    async def draft_outreach(self, **kwargs: Any) -> DraftOutput:
        text = await self._chat(
            "Write a short sales email using ONLY the provided facts. "
            "No website-research claims, no prior-contact claims.",
            f"Draft email for {kwargs}",
        )
        if not text or len(text.strip()) < 10:
            raise ProviderMalformedError("Empty model response")
        lines = [line for line in text.splitlines() if line.strip()]
        subject = lines[0][:500] if lines else f"Quick idea for {kwargs.get('company')}"
        return DraftOutput(
            subject=subject, body=text[:5000], evidence=list(kwargs.get("evidence", []))
        )


def get_provider():
    if settings.ai_provider == "openai_compatible" and settings.openai_api_key:
        log.info("Using live AI provider: openai_compatible")
        return OpenAICompatibleProvider()
    return MockProvider()


def provider_status() -> dict:
    live = settings.ai_provider == "openai_compatible" and bool(settings.openai_api_key)
    return {
        "configured_provider": settings.ai_provider,
        "active_provider": "openai_compatible" if live else "mock",
        "mock_mode": not live,
        "timeout_seconds": settings.ai_timeout_seconds,
        "max_retries": settings.ai_max_retries,
        "token_budget": settings.ai_max_tokens,
    }
