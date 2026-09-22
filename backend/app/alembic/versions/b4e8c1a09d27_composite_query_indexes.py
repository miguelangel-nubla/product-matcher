"""Replace single-column indexes with composites used by list queries

Revision ID: b4e8c1a09d27
Revises: c7a9e1d2f345
Create Date: 2026-09-22 16:10:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "b4e8c1a09d27"
down_revision = "c7a9e1d2f345"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index(op.f("ix_pendingquery_owner_id"), table_name="pendingquery")
    op.drop_index(op.f("ix_pendingquery_status"), table_name="pendingquery")
    op.drop_index(op.f("ix_pendingquery_created_at"), table_name="pendingquery")
    op.drop_index(op.f("ix_matchlog_owner_id"), table_name="matchlog")
    op.drop_index(op.f("ix_matchlog_created_at"), table_name="matchlog")
    op.create_index(
        "ix_pendingquery_owner_status_created",
        "pendingquery",
        ["owner_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_matchlog_owner_created",
        "matchlog",
        ["owner_id", "created_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_matchlog_owner_created", table_name="matchlog")
    op.drop_index("ix_pendingquery_owner_status_created", table_name="pendingquery")
    op.create_index(
        op.f("ix_matchlog_created_at"), "matchlog", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_matchlog_owner_id"), "matchlog", ["owner_id"], unique=False
    )
    op.create_index(
        op.f("ix_pendingquery_created_at"),
        "pendingquery",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pendingquery_status"), "pendingquery", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_pendingquery_owner_id"), "pendingquery", ["owner_id"], unique=False
    )
