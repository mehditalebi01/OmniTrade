from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from threading import RLock
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from omnitrade.config import get_settings
from omnitrade.contracts import Run, RunEvent, UserProfile, WorkflowDefinition, WorkflowVersion
from omnitrade.db import (
    EventRow,
    ProfileRow,
    ReportRow,
    RunRow,
    WorkflowRow,
    WorkflowVersionRow,
    engine,
)


class NotFoundError(KeyError):
    pass


class InMemoryStore:
    """Thread-safe development store; PostgreSQL is used by the Compose profile."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.workflows: dict[UUID, dict[str, Any]] = {}
        self.versions: dict[UUID, WorkflowVersion] = {}
        self.runs: dict[UUID, Run] = {}
        self.run_events: dict[UUID, list[RunEvent]] = defaultdict(list)
        self.run_results: dict[UUID, dict[str, Any]] = {}
        self.profiles: dict[UUID, UserProfile] = {}

    def create_workflow(self, owner_id: UUID, definition: WorkflowDefinition) -> dict[str, Any]:
        with self._lock:
            workflow_id = uuid4()
            record = {
                "id": workflow_id,
                "owner_id": owner_id,
                "definition": definition,
                "version": 0,
                "published_version_id": None,
            }
            self.workflows[workflow_id] = record
            return record.copy()

    def list_workflows(self, owner_id: UUID) -> list[dict[str, Any]]:
        return [
            record.copy() for record in self.workflows.values() if record["owner_id"] == owner_id
        ]

    def get_workflow(self, workflow_id: UUID, owner_id: UUID) -> dict[str, Any]:
        record = self.workflows.get(workflow_id)
        if not record or record["owner_id"] != owner_id:
            raise NotFoundError(workflow_id)
        return record

    def update_workflow(
        self, workflow_id: UUID, owner_id: UUID, definition: WorkflowDefinition
    ) -> dict[str, Any]:
        with self._lock:
            record = self.get_workflow(workflow_id, owner_id)
            record["definition"] = definition
            return record.copy()

    def delete_workflow(self, workflow_id: UUID, owner_id: UUID) -> None:
        with self._lock:
            self.get_workflow(workflow_id, owner_id)
            del self.workflows[workflow_id]

    def publish(self, workflow_id: UUID, owner_id: UUID) -> WorkflowVersion:
        with self._lock:
            record = self.get_workflow(workflow_id, owner_id)
            record["version"] += 1
            canonical = json.dumps(
                record["definition"].model_dump(mode="json"), sort_keys=True, separators=(",", ":")
            )
            version = WorkflowVersion(
                workflow_id=workflow_id,
                version=record["version"],
                definition=record["definition"].model_copy(deep=True),
                published=True,
                content_hash=hashlib.sha256(canonical.encode()).hexdigest(),
            )
            self.versions[version.id] = version
            record["published_version_id"] = version.id
            return version

    def add_event(self, event: RunEvent) -> None:
        with self._lock:
            if all(current.event_id != event.event_id for current in self.run_events[event.run_id]):
                self.run_events[event.run_id].append(event)

    def save_run(self, run: Run) -> None:
        self.runs[run.id] = run

    def save_result(self, run_id: UUID, result: dict[str, Any]) -> None:
        self.run_results[run_id] = result

    def list_runs(self, owner_id: UUID) -> list[Run]:
        return sorted(
            (run for run in self.runs.values() if run.owner_id == owner_id),
            key=lambda run: run.created_at,
            reverse=True,
        )

    def get_profile(self, owner_id: UUID) -> UserProfile:
        return self.profiles.setdefault(owner_id, UserProfile())

    def save_profile(self, owner_id: UUID, profile: UserProfile) -> UserProfile:
        self.profiles[owner_id] = profile
        return profile


class PostgresStore(InMemoryStore):
    """Durable Compose store. Caches speed local reads but every mutation is committed."""

    def __init__(self) -> None:
        super().__init__()
        self.sessions: sessionmaker[Session] = sessionmaker(engine(), expire_on_commit=False)
        self._load()

    def _load(self) -> None:
        with self.sessions() as session:
            for profile_row in session.scalars(select(ProfileRow)):
                self.profiles[profile_row.owner_id] = UserProfile.model_validate(profile_row.body)
            for workflow_row in session.scalars(select(WorkflowRow)):
                definition = WorkflowDefinition.model_validate(workflow_row.draft)
                self.workflows[workflow_row.id] = {
                    "id": workflow_row.id,
                    "owner_id": workflow_row.owner_id,
                    "definition": definition,
                    "version": 0,
                    "published_version_id": None,
                }
            for version_row in session.scalars(
                select(WorkflowVersionRow).order_by(WorkflowVersionRow.version)
            ):
                version = WorkflowVersion(
                    id=version_row.id,
                    workflow_id=version_row.workflow_id,
                    version=version_row.version,
                    definition=WorkflowDefinition.model_validate(version_row.definition),
                    published=True,
                    content_hash=version_row.content_hash,
                )
                self.versions[version_row.id] = version
                if version_row.workflow_id in self.workflows:
                    self.workflows[version_row.workflow_id]["version"] = version_row.version
                    self.workflows[version_row.workflow_id]["published_version_id"] = version_row.id
            for run_row in session.scalars(select(RunRow)):
                self.runs[run_row.id] = Run(
                    id=run_row.id,
                    workflow_version_id=run_row.workflow_version_id,
                    owner_id=run_row.owner_id,
                    ticker=run_row.ticker,
                    as_of=run_row.as_of,
                    status=run_row.status,
                    trace_id=run_row.trace_id,
                    degraded_reasons=run_row.degraded_reasons or [],
                    configuration=run_row.configuration or {},
                    budget_override=run_row.budget_override,
                    created_at=run_row.created_at,
                    updated_at=run_row.updated_at,
                )
            for event_row in session.scalars(select(EventRow).order_by(EventRow.occurred_at)):
                self.run_events[event_row.run_id].append(
                    RunEvent(
                        schema_version=event_row.schema_version,
                        event_id=event_row.event_id,
                        event_type=event_row.event_type,
                        run_id=event_row.run_id,
                        node_id=event_row.node_id,
                        trace_id=event_row.trace_id,
                        occurred_at=event_row.occurred_at,
                        payload=event_row.payload,
                    )
                )
            for report_row in session.scalars(select(ReportRow)):
                self.run_results[report_row.run_id] = {
                    "report": report_row.decision,
                    "nodes": report_row.lineage,
                }

    def create_workflow(self, owner_id: UUID, definition: WorkflowDefinition) -> dict[str, Any]:
        record = super().create_workflow(owner_id, definition)
        with self.sessions.begin() as session:
            session.add(
                WorkflowRow(
                    id=record["id"],
                    owner_id=owner_id,
                    name=definition.name,
                    draft=definition.model_dump(mode="json"),
                )
            )
        return record

    def update_workflow(
        self, workflow_id: UUID, owner_id: UUID, definition: WorkflowDefinition
    ) -> dict[str, Any]:
        record = super().update_workflow(workflow_id, owner_id, definition)
        with self.sessions.begin() as session:
            row = session.get(WorkflowRow, workflow_id)
            if row:
                row.name = definition.name
                row.draft = definition.model_dump(mode="json")
        return record

    def delete_workflow(self, workflow_id: UUID, owner_id: UUID) -> None:
        super().delete_workflow(workflow_id, owner_id)
        with self.sessions.begin() as session:
            session.execute(
                delete(WorkflowVersionRow).where(WorkflowVersionRow.workflow_id == workflow_id)
            )
            row = session.get(WorkflowRow, workflow_id)
            if row:
                session.delete(row)

    def publish(self, workflow_id: UUID, owner_id: UUID) -> WorkflowVersion:
        version = super().publish(workflow_id, owner_id)
        with self.sessions.begin() as session:
            session.add(
                WorkflowVersionRow(
                    id=version.id,
                    workflow_id=workflow_id,
                    version=version.version,
                    definition=version.definition.model_dump(mode="json"),
                    content_hash=version.content_hash,
                )
            )
        return version

    def save_run(self, run: Run) -> None:
        super().save_run(run)
        with self.sessions.begin() as session:
            session.merge(
                RunRow(
                    id=run.id,
                    workflow_version_id=run.workflow_version_id,
                    owner_id=run.owner_id,
                    ticker=run.ticker,
                    status=run.status,
                    trace_id=run.trace_id,
                    as_of=run.as_of,
                    degraded_reasons=run.degraded_reasons,
                    configuration=run.configuration.model_dump(mode="json"),
                    budget_override=(
                        run.budget_override.model_dump(mode="json") if run.budget_override else None
                    ),
                    created_at=run.created_at,
                    updated_at=run.updated_at,
                )
            )

    def save_profile(self, owner_id: UUID, profile: UserProfile) -> UserProfile:
        super().save_profile(owner_id, profile)
        with self.sessions.begin() as session:
            session.merge(ProfileRow(owner_id=owner_id, body=profile.model_dump(mode="json")))
        return profile

    def add_event(self, event: RunEvent) -> None:
        if any(current.event_id == event.event_id for current in self.run_events[event.run_id]):
            return
        super().add_event(event)
        with self.sessions.begin() as session:
            session.add(
                EventRow(
                    event_id=event.event_id,
                    run_id=event.run_id,
                    event_type=event.event_type,
                    node_id=event.node_id,
                    payload=event.payload,
                    trace_id=event.trace_id,
                    occurred_at=event.occurred_at,
                    schema_version=event.schema_version,
                )
            )

    def save_result(self, run_id: UUID, result: dict[str, Any]) -> None:
        super().save_result(run_id, result)
        with self.sessions.begin() as session:
            existing = session.scalar(select(ReportRow).where(ReportRow.run_id == run_id))
            if existing:
                existing.decision = result.get("report", {})
                existing.lineage = result.get("nodes", {})
            else:
                session.add(
                    ReportRow(
                        run_id=run_id,
                        decision=result.get("report", {}),
                        lineage=result.get("nodes", {}),
                    )
                )


store: InMemoryStore = (
    PostgresStore() if get_settings().database_url.startswith("postgresql") else InMemoryStore()
)
