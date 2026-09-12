from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

from fastapi.testclient import TestClient

# The measurement is local and deterministic. It must not depend on a running
# Compose database or call external financial/model providers.
os.environ["OMNITRADE_ENV"] = "quality-measurement"
os.environ["OMNITRADE_FIXTURE_MODE"] = "true"
os.environ["OMNITRADE_DATABASE_URL"] = "sqlite:///./quality-omnitrade.db"
os.environ["OMNITRADE_REDIS_URL"] = "redis://localhost:6379/15"
os.environ["OMNITRADE_JWT_SECRET"] = "quality-measurement-key-at-least-32-bytes-long"

from omnitrade.api import app
from omnitrade.engine.validator import WorkflowValidator
from omnitrade.quality import MetricDirection, QualityTarget, evaluate_metric
from omnitrade.sample_workflow import defense_workflow

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "artifacts" / "quality" / "nfr-measurements.json"


def measure_ms(action, *, warmups: int, samples: int) -> list[float]:
    for _ in range(warmups):
        action()
    values: list[float] = []
    for _ in range(samples):
        started = perf_counter()
        action()
        values.append((perf_counter() - started) * 1000)
    return values


def main() -> int:
    validator = WorkflowValidator()
    graph = defense_workflow()
    validation_samples = measure_ms(lambda: validator.validate(graph), warmups=5, samples=50)
    validation = evaluate_metric(
        QualityTarget(
            requirement_id="NFR-04",
            metric="Reference-workflow validation p95",
            direction=MetricDirection.AT_MOST,
            threshold=100.0,
            unit="ms",
        ),
        validation_samples,
    )

    with TestClient(app) as client:
        login = client.post("/api/v1/auth/login", json={"username": "demo", "password": "demo"})
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        def read_profile() -> None:
            response = client.get("/api/v1/profile", headers=headers)
            response.raise_for_status()

        api_samples = measure_ms(read_profile, warmups=5, samples=40)
        api_read = evaluate_metric(
            QualityTarget(
                requirement_id="NFR-03",
                metric="Authenticated local API read p95",
                direction=MetricDirection.AT_MOST,
                threshold=500.0,
                unit="ms",
            ),
            api_samples,
        )

    route_paths = sorted(str(route.path) for route in app.routes if hasattr(route, "path"))
    forbidden_routes = [
        path
        for path in route_paths
        if any(word in path.lower() for word in ("/broker", "/orders", "/trade-execution"))
    ]
    safety = {
        "requirement_id": "NFR-07",
        "metric": "Forbidden broker/order API routes",
        "observed": len(forbidden_routes),
        "threshold": 0,
        "unit": "routes",
        "passed": not forbidden_routes,
        "details": forbidden_routes,
    }

    results = [asdict(api_read), asdict(validation), safety]
    evidence = {
        "method": "Local deterministic quality measurement; external providers are not called.",
        "results": results,
        "all_passed": all(result["passed"] for result in results),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return 0 if evidence["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
