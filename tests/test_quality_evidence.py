from omnitrade.config import Settings
from omnitrade.quality import MetricDirection, QualityTarget, evaluate_metric, percentile


def test_nfr_03_percentile_uses_nearest_rank_for_latency_evidence() -> None:
    assert percentile([10.0, 20.0, 30.0, 40.0], 0.95) == 40.0


def test_snfr_quality_gate_reports_observation_target_and_result() -> None:
    target = QualityTarget(
        requirement_id="NFR-03",
        metric="Local API read latency p95",
        direction=MetricDirection.AT_MOST,
        threshold=500.0,
        unit="ms",
    )

    passed = evaluate_metric(target, [20.0, 45.0, 120.0])
    failed = evaluate_metric(target, [250.0, 510.0, 700.0])

    assert passed.requirement_id == "NFR-03"
    assert passed.observed == 120.0
    assert passed.threshold == 500.0
    assert passed.passed is True
    assert failed.passed is False


def test_nfr_quality_gate_supports_minimum_targets() -> None:
    target = QualityTarget(
        requirement_id="NFR-08",
        metric="Workflow-core statement coverage",
        direction=MetricDirection.AT_LEAST,
        threshold=80.0,
        unit="percent",
    )

    assert evaluate_metric(target, [89.37]).passed is True
    assert evaluate_metric(target, [79.99]).passed is False


def test_nfr_02_default_jwt_secret_meets_hs256_minimum_length(monkeypatch) -> None:
    monkeypatch.delenv("OMNITRADE_JWT_SECRET", raising=False)
    settings = Settings(_env_file=None)

    assert len(settings.jwt_secret.encode("utf-8")) >= 32
