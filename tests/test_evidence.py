from datetime import UTC, datetime, timedelta

import pytest

from omnitrade.evidence import EvidencePolicy, EvidenceQualityError, RawEvidence, validate_evidence


def item(observed):
    return RawEvidence(
        ticker="AAPL", observed_at=observed, provider="fixture", value=10, currency="EUR"
    )


def test_evidence_flags_conversion_and_missing_metadata():
    now = datetime.now(UTC)
    flags = validate_evidence(item(now - timedelta(hours=1)), "AAPL", now, EvidencePolicy())
    assert set(flags) == {"currency_conversion_required", "unit_missing", "source_url_missing"}


def test_rejects_future_and_stale_evidence():
    now = datetime.now(UTC)
    with pytest.raises(EvidenceQualityError):
        validate_evidence(item(now + timedelta(minutes=1)), "AAPL", now, EvidencePolicy())
    with pytest.raises(EvidenceQualityError):
        validate_evidence(item(now - timedelta(days=10)), "AAPL", now, EvidencePolicy())
