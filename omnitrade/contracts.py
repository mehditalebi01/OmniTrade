from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


class PortType(StrEnum):
    CONTROL = "control"
    INSTRUMENT = "instrument"
    RAW_MARKET = "raw_market"
    RAW_FUNDAMENTALS = "raw_fundamentals"
    RAW_TEXT = "raw_text"
    NORMALIZED_MARKET = "normalized_market"
    NORMALIZED_FUNDAMENTALS = "normalized_fundamentals"
    NORMALIZED_TEXT = "normalized_text"
    EVIDENCE = "evidence"
    EVIDENCE_SET = "evidence_set"
    SPECIALIST_REPORT = "specialist_report"
    SPECIALIST_REPORTS = "specialist_reports"
    RESEARCH_CASE = "research_case"
    RESEARCH_CASES = "research_cases"
    PROPOSAL = "proposal"
    RISK_VIEW = "risk_view"
    RISK_VIEWS = "risk_views"
    DECISION = "decision"
    REPORT = "report"


class FailurePolicy(StrEnum):
    REQUIRED = "required"
    OPTIONAL = "optional"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DEGRADED = "degraded"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PAUSING = "pausing"
    PAUSED = "paused"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class NodeStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    DEGRADED = "degraded"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=1, ge=1, le=5)
    backoff_ms: int = Field(default=100, ge=0, le=30_000)
    fallback_provider: str | None = None


class NodeDefinition(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$")
    type: str
    name: str = Field(min_length=1, max_length=120)
    config: dict[str, Any] = Field(default_factory=dict)
    failure_policy: FailurePolicy = FailurePolicy.REQUIRED
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})


class EdgeDefinition(BaseModel):
    id: str
    source: str
    source_port: str
    target: str
    target_port: str
    loop: bool = False


class Budget(BaseModel):
    max_runtime_seconds: int = Field(default=180, ge=10, le=1800)
    max_model_calls: int = Field(default=20, ge=0, le=100)
    max_provider_calls: int = Field(default=30, ge=0, le=200)
    max_tokens: int = Field(default=40_000, ge=0, le=1_000_000)
    max_parallel_nodes: int = Field(default=8, ge=1, le=32)


class RunConfiguration(BaseModel):
    """User choices that make one analysis run reproducible."""

    data_mode: str = Field(default="live", pattern=r"^(recorded|prefer_live|live)$")
    analysts: list[str] = Field(
        default_factory=lambda: ["market", "fundamentals", "news", "sentiment"]
    )
    research_depth: int = Field(default=2, ge=1, le=5)
    risk_profile: str = Field(default="balanced", pattern=r"^(conservative|balanced|aggressive)$")
    report_detail: str = Field(default="standard", pattern=r"^(summary|standard|detailed)$")
    output_language: str = Field(default="English", min_length=2, max_length=40)
    base_currency: str = Field(default="USD", min_length=3, max_length=3)
    allow_degraded: bool = True
    evidence_freshness_hours: int = Field(default=72, ge=1, le=720)
    quick_model: str = Field(default="deterministic-fixture", min_length=2, max_length=100)
    deep_model: str = Field(default="deterministic-fixture", min_length=2, max_length=100)
    model_provider: str = Field(default="fixture", min_length=2, max_length=40)
    market_providers: list[str] = Field(default_factory=lambda: ["yfinance"])
    fundamental_providers: list[str] = Field(default_factory=lambda: ["yfinance"])
    news_providers: list[str] = Field(default_factory=lambda: ["yfinance"])
    sentiment_providers: list[str] = Field(default_factory=lambda: ["yfinance"])
    macro_providers: list[str] = Field(default_factory=lambda: ["fred"])
    temperature: float | None = Field(default=None, ge=0, le=2)
    model_max_retries: int = Field(default=2, ge=0, le=5)
    reasoning_effort: str = Field(default="medium", pattern=r"^(low|medium|high)$")

    @model_validator(mode="after")
    def valid_analysts(self) -> RunConfiguration:
        allowed = {"market", "fundamentals", "news", "sentiment"}
        if not self.analysts or not set(self.analysts).issubset(allowed):
            raise ValueError("analysts must contain supported values")
        category_allowed = (
            (self.market_providers, {"yfinance", "alpha_vantage"}),
            (self.fundamental_providers, {"yfinance", "alpha_vantage"}),
            (self.news_providers, {"yfinance", "alpha_vantage"}),
            (self.sentiment_providers, {"yfinance", "alpha_vantage", "stocktwits", "reddit"}),
            (self.macro_providers, {"alpha_vantage", "fred", "polymarket"}),
        )
        if any(
            not chain or not set(chain).issubset(allowed) for chain, allowed in category_allowed
        ):
            raise ValueError("every data category needs a compatible real provider chain")
        return self


class InvestorPolicy(BaseModel):
    """User investment constraints that change risk validation, not raw evidence."""

    investment_horizon: str = Field(default="medium", pattern=r"^(short|medium|long)$")
    experience_level: str = Field(default="beginner", pattern=r"^(beginner|intermediate|advanced)$")
    maximum_loss_percent: float = Field(default=10, ge=1, le=50)
    maximum_position_percent: float = Field(default=20, ge=1, le=100)
    excluded_sectors: list[str] = Field(default_factory=list, max_length=20)


class UserProfile(BaseModel):
    display_name: str = Field(default="OmniTrade Student", min_length=2, max_length=100)
    email: str = Field(default="", max_length=160)
    default_ticker: str = Field(default="AAPL", pattern=r"^[A-Z][A-Z0-9.-]*$")
    default_configuration: RunConfiguration = Field(default_factory=RunConfiguration)
    investor_policy: InvestorPolicy = Field(default_factory=InvestorPolicy)


class WorkflowDefinition(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=1000)
    nodes: list[NodeDefinition]
    edges: list[EdgeDefinition]
    budget: Budget = Field(default_factory=Budget)
    schema_version: str = "1.0"

    @model_validator(mode="after")
    def unique_ids(self) -> WorkflowDefinition:
        node_ids = [node.id for node in self.nodes]
        edge_ids = [edge.id for edge in self.edges]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("node IDs must be unique")
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("edge IDs must be unique")
        return self


class WorkflowVersion(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID = Field(default_factory=uuid4)
    version: int = Field(ge=1)
    definition: WorkflowDefinition
    published: bool = False
    content_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ValidationIssue(BaseModel):
    code: str
    message: str
    node_id: str | None = None
    edge_id: str | None = None


class ValidationResult(BaseModel):
    valid: bool
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)


class RunRequest(BaseModel):
    workflow_version_id: UUID
    ticker: str = Field(min_length=1, max_length=10, pattern=r"^[A-Z][A-Z0-9.-]*$")
    as_of: datetime
    budget_override: Budget | None = None
    configuration: RunConfiguration = Field(default_factory=RunConfiguration)

    @model_validator(mode="after")
    def as_of_not_future(self) -> RunRequest:
        if self.as_of > datetime.now(UTC):
            raise ValueError("as_of cannot be in the future")
        return self


class Run(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    workflow_version_id: UUID
    owner_id: UUID
    ticker: str
    as_of: datetime
    status: RunStatus = RunStatus.QUEUED
    trace_id: UUID = Field(default_factory=uuid4)
    degraded_reasons: list[str] = Field(default_factory=list)
    configuration: RunConfiguration = Field(default_factory=RunConfiguration)
    investor_policy: InvestorPolicy = Field(default_factory=InvestorPolicy)
    budget_override: Budget | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NodeRun(BaseModel):
    run_id: UUID
    node_id: str
    status: NodeStatus = NodeStatus.PENDING
    attempt: int = 0
    iteration: int = 0
    output: Any = None
    error: str | None = None


class RunEvent(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    run_id: UUID
    node_id: str | None = None
    trace_id: UUID
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    ticker: str
    evidence_type: str
    value: Any
    unit: str | None = None
    currency: str | None = None
    observed_at: datetime
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    provider: str
    source_url: str | None = None
    content_hash: str
    quality_flags: list[str] = Field(default_factory=list)


class Claim(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    text: str
    evidence_ids: list[UUID]
    confidence: float = Field(ge=0, le=1)


class AgentReport(BaseModel):
    specialist: str
    summary: str
    claims: list[Claim]
    risks: list[str] = Field(default_factory=list)


class Decision(BaseModel):
    action: str = Field(pattern=r"^(BUY|HOLD|SELL|NO_DECISION)$")
    confidence: float = Field(ge=0, le=1)
    rationale: str
    claim_ids: list[UUID]
    warnings: list[str] = Field(default_factory=list)


class Checkpoint(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    sequence: int = Field(ge=0)
    node_states: dict[str, NodeRun]
    consumed_event_ids: set[UUID] = Field(default_factory=set)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Artifact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    report_id: UUID
    format: str
    path: str
    sha256: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
