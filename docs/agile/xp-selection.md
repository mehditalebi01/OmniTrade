# Agile XP selection rationale

## Decision

OmniTrade uses Agile development with Extreme Programming (XP) as the main
software development process. Backlog ordering, iteration review, and
retrospective are lightweight planning practices; they do not replace XP's
test-first engineering cycle.

## Project conditions

- The team has two student developers, so direct communication and collective
  ownership are practical.
- The fixed boundary is clear: stocks, decision support, no broker execution.
  Detailed provider, workflow, recovery, and interface needs changed after
  demonstrations and defects.
- The most risky behavior is executable and testable: graph rules, concurrency,
  failure propagation, checkpoints, configuration combinations, and lineage.
- External providers and models change and fail, so small adapter changes and
  continuous regression feedback are more useful than one final integration.
- The course requires visible working increments and evidence, not only a final
  document.

## Comparison

| Process choice | Fit | Main limitation for OmniTrade | Decision |
|---|---|---|---|
| Plan-driven waterfall | Useful when requirements are stable and formal approval must freeze each phase. | Provider behavior, GUI use, configuration combinations, and recovery defects were learned through working software; late integration would hide risk. | Rejected as main process. |
| Scrum without XP engineering practices | Useful for team coordination, backlog, and review. | It does not by itself define test-first coding, refactoring, simple design, pairing/review, or continuous integration. | Planning practices only. |
| Kanban | Useful for continuous support flow and work limits. | It gives less structure for eight course increments and story acceptance. | Useful later for maintenance, not the main development process. |
| Reuse-oriented development | Useful for frameworks, providers, and pretrained models. | Reusing a workflow framework would hide the assessed custom validator, scheduler, recovery, and lineage logic. | Applied only to supporting components. |
| Agile XP | Small stories, Planning Game, on-site feedback adaptation, TDD, refactoring, CI, simple design, collective ownership, and frequent releases. | Requires discipline and strong automated tests; a two-person team must adapt roles honestly. | Selected. |

## XP practices used and adaptation

- Planning Game: choose ready stories by value, risk, dependency, and MoSCoW.
- Small releases: eight vertical increments plus a professor-review revision.
- TDD: Red, Green, Refactor, integration, story acceptance, and regression.
- Simple design: implement the smallest contract that satisfies the selected story.
- Refactoring: improve structure only with passing focused and regression tests.
- Continuous integration: backend, frontend, types, lint, migration, build, and browser gates.
- Collective ownership: both students may change any component; lead and reviewer rotate.
- Pair review: one leads and one reviews; continuous pair programming is not claimed.
- Customer feedback adaptation: the professor approves academic scope but is not
  an operational product actor. Working demonstrations, student user journeys,
  and professor review supply feedback because no full-time customer is present.
- Sustainable pace: story points estimate relative size; planned hours protect
  the course schedule and are not used to compare developer performance.

## Main trade-off

XP lets the team learn early and provides strong executable evidence, but it
does not remove the need for a controlled requirement catalog, UML design, or
system-level verification. These artifacts are kept lightweight, versioned, and
updated inside each increment rather than written once before coding.
