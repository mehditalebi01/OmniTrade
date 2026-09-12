from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field


class RawEvidence(BaseModel):
    ticker: str
    observed_at: datetime
    provider: str
    value: Any
    unit: str | None = None
    currency: str | None = None
    source_url: str | None = None


class EvidencePolicy(BaseModel):
    max_age: timedelta = Field(default=timedelta(hours=72))
    required_currency: str = "USD"
    allowed_providers: set[str] = Field(default_factory=set)


class EvidenceQualityError(ValueError):
    pass


def validate_evidence(
    item: RawEvidence, ticker: str, as_of: datetime, policy: EvidencePolicy
) -> list[str]:
    flags: list[str] = []
    if item.ticker != ticker:
        raise EvidenceQualityError("ticker mismatch")
    if item.observed_at > as_of:
        raise EvidenceQualityError("look-ahead evidence is forbidden")
    if as_of - item.observed_at > policy.max_age:
        raise EvidenceQualityError("evidence is stale")
    if policy.allowed_providers and item.provider not in policy.allowed_providers:
        raise EvidenceQualityError("provider is not allowed")
    if item.currency and item.currency != policy.required_currency:
        flags.append("currency_conversion_required")
    if item.unit is None:
        flags.append("unit_missing")
    if item.source_url is None:
        flags.append("source_url_missing")
    if item.observed_at.tzinfo is None or item.observed_at.utcoffset() is None:
        raise EvidenceQualityError("timestamp must include timezone")
    return flags
