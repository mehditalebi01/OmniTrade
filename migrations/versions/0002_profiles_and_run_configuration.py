"""Profiles and reproducible analysis configuration."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    # Revision 0001 uses live model metadata, so fresh installs can already
    # contain these objects. Older databases still need them added here.
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("profiles", schema="api"):
        op.create_table(
            "profiles",
            sa.Column("owner_id", sa.Uuid(), primary_key=True),
            sa.Column("body", sa.JSON(), nullable=False),
            schema="api",
        )
    existing = {column["name"] for column in inspector.get_columns("runs", schema="workflow")}
    columns = (
        sa.Column("configuration", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("budget_override", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in columns:
        if column.name not in existing:
            op.add_column("runs", column, schema="workflow")


def downgrade():
    for column in ("updated_at", "created_at", "budget_override", "configuration"):
        op.drop_column("runs", column, schema="workflow")
    op.drop_table("profiles", schema="api")
