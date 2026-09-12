from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from omnitrade.config import get_settings


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "api"}
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))


class ProfileRow(Base):
    __tablename__ = "profiles"
    __table_args__ = {"schema": "api"}
    owner_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    body: Mapped[dict[str, Any]] = mapped_column(JSON)


class WorkflowRow(Base):
    __tablename__ = "workflows"
    __table_args__ = {"schema": "workflow"}
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    name: Mapped[str] = mapped_column(String(120))
    draft: Mapped[dict[str, Any]] = mapped_column(JSON)


class WorkflowVersionRow(Base):
    __tablename__ = "workflow_versions"
    __table_args__ = {"schema": "workflow"}
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workflow_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("workflow.workflows.id"))
    version: Mapped[int]
    definition: Mapped[dict[str, Any]] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))


class RunRow(Base):
    __tablename__ = "runs"
    __table_args__ = {"schema": "workflow"}
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workflow_version_id: Mapped[UUID] = mapped_column(Uuid)
    owner_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    ticker: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(30), index=True)
    trace_id: Mapped[UUID] = mapped_column(Uuid)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    degraded_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    budget_override: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EventRow(Base):
    __tablename__ = "events"
    __table_args__ = {"schema": "workflow"}
    event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    run_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    node_id: Mapped[str | None] = mapped_column(String(80))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    trace_id: Mapped[UUID] = mapped_column(Uuid)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    schema_version: Mapped[str] = mapped_column(String(20), default="1.0")


class EvidenceRow(Base):
    __tablename__ = "evidence"
    __table_args__ = {"schema": "evidence"}
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    ticker: Mapped[str] = mapped_column(String(10))
    provider: Mapped[str] = mapped_column(String(80))
    content_hash: Mapped[str] = mapped_column(String(64))
    body: Mapped[dict[str, Any]] = mapped_column(JSON)


class ModelCallRow(Base):
    __tablename__ = "model_calls"
    __table_args__ = {"schema": "model"}
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    model: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30))
    tokens: Mapped[int]


class ReportRow(Base):
    __tablename__ = "reports"
    __table_args__ = {"schema": "report"}
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(Uuid, unique=True)
    decision: Mapped[dict[str, Any]] = mapped_column(JSON)
    lineage: Mapped[dict[str, Any]] = mapped_column(JSON)


class ArtifactRow(Base):
    __tablename__ = "artifacts"
    __table_args__ = {"schema": "report"}
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    report_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("report.reports.id"))
    format: Mapped[str] = mapped_column(String(20))
    path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))


def engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)
