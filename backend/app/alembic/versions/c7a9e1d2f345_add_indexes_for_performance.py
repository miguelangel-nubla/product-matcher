"""Add indexes for performance

Revision ID: c7a9e1d2f345
Revises: 896b5bf4f91b
Create Date: 2026-09-22 15:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7a9e1d2f345'
down_revision = '896b5bf4f91b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(op.f('ix_accesstoken_prefix'), 'accesstoken', ['prefix'], unique=False)
    op.create_index(op.f('ix_pendingquery_owner_id'), 'pendingquery', ['owner_id'], unique=False)
    op.create_index(op.f('ix_pendingquery_status'), 'pendingquery', ['status'], unique=False)
    op.create_index(op.f('ix_pendingquery_created_at'), 'pendingquery', ['created_at'], unique=False)
    op.create_index(op.f('ix_matchlog_owner_id'), 'matchlog', ['owner_id'], unique=False)
    op.create_index(op.f('ix_matchlog_created_at'), 'matchlog', ['created_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_matchlog_created_at'), table_name='matchlog')
    op.drop_index(op.f('ix_matchlog_owner_id'), table_name='matchlog')
    op.drop_index(op.f('ix_pendingquery_created_at'), table_name='pendingquery')
    op.drop_index(op.f('ix_pendingquery_status'), table_name='pendingquery')
    op.drop_index(op.f('ix_pendingquery_owner_id'), table_name='pendingquery')
    op.drop_index(op.f('ix_accesstoken_prefix'), table_name='accesstoken')
