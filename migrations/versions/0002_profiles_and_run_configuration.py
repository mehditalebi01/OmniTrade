"""Profiles and reproducible analysis configuration."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "profiles",
        sa.Column("owner_id", sa.Uuid(), primary_key=True),
        sa.Column("body", sa.JSON(), nullable=False),
        schema="api",
    )
    op.add_column("runs", sa.Column("configuration", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")), schema="workflow")
    op.add_column("runs", sa.Column("budget_override", sa.JSON(), nullable=True), schema="workflow")
    op.add_column("runs", sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), schema="workflow")
    op.add_column("runs", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), schema="workflow")


def downgrade():
    for column in ("updated_at", "created_at", "budget_override", "configuration"):
        op.drop_column("runs", column, schema="workflow")
    op.drop_table("profiles", schema="api")
