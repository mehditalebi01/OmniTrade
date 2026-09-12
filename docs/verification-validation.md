# Verification, validation, and acceptance evidence

## Difference

Verification asks whether the product is built according to its system
requirements and design. Validation asks whether the working product solves the
user needs in its intended context. XP performs both continuously: focused tests
verify each change, while story confirmation and working demonstrations validate
the increment.

## TDD verification flow

1. Select one ready story and linked UR/FR/NFR IDs.
2. Write acceptance examples and the smallest failing test (Red).
3. Confirm the failure is caused by missing/incorrect behavior.
4. Implement the smallest change (Green).
5. Refactor while focused tests remain green.
6. Run unit, property, contract, integration, API, frontend, and static checks.
7. Run requirement acceptance and the complete regression suite.
8. Demonstrate the vertical user journey and record acceptance or feedback.
9. Update UML, traceability, evidence, and retrospective.

## Test levels and purpose

| Level | Verification concern | Example |
|---|---|---|
| Unit / property | Local formula or invariant over many inputs | graph validator, evidence time gate, percentile gate |
| Component | One service behind typed contracts | provider adapter, model gateway, report builder |
| Contract | Request/response, event, provider/model schema | invalid model output and safe provider error |
| Integration | Several real internal components | scheduler + events + checkpoint + persistence |
| System / browser | Complete user path | login, configure, run, monitor, report, recover, graph correction |
| Resilience / security | Abnormal and hostile conditions | required/optional failure, duplicate event, expired token, secret canary |
| Performance | Measurable NFR thresholds | API and validator p95, concurrency/call limits |
| Deployment / release | Reproducible complete environment | migration order, eight healthy services, restart/reload |

## Acceptance records

- FR acceptance uses stable TC IDs in `docs/requirements.md` and concrete test
  names in `docs/traceability.md`.
- NFR acceptance uses an explicit metric, environment, sample size, threshold,
  and pass rule. `scripts/measure_quality.py` writes observed JSON evidence.
- A story is accepted only when its confirmation passes in integrated software.
- A passing unit test does not validate the user need by itself.
- Live provider/model checks are separate because changing external data is not
  deterministic. CI uses explicit test seams and production rejects them.

## Definition of Done

A story is Done when its confirmation passes; linked FR/NFR gates pass; code is
reviewed; types/lint/tests/build are green; security, data, migration, recovery,
and documentation effects are considered; UML and traceability are updated; no
new critical defect exists; and the increment is demonstrated. Missing evidence
means Not Done, not "assumed passed".

## Evidence limitations

Coverage measures executed code, not economic truth. Provider verification is a
point-in-time capability check. Model output remains non-deterministic. A local
latency result applies only to the stated environment. Manual accessibility and
clean-host deployment evidence must remain visibly separate from automated unit
results.
