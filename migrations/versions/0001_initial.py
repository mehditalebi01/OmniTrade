"""Initial service-owned schemas and tables."""
from alembic import op
from omnitrade.db import Base
revision="0001";down_revision=None;branch_labels=None;depends_on=None
def upgrade():
    bind=op.get_bind()
    for schema in ("api","workflow","evidence","model","report"):op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    Base.metadata.create_all(bind=bind)
def downgrade():
    bind=op.get_bind();Base.metadata.drop_all(bind=bind)
    for schema in ("report","model","evidence","workflow","api"):op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
