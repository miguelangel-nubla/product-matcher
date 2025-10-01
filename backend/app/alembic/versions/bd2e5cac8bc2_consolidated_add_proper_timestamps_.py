"""Consolidated: Add proper timestamps, threshold, and backend fields

Revision ID: bd2e5cac8bc2
Revises: 090498e10a94
Create Date: 2025-10-01 23:56:20.661864

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'bd2e5cac8bc2'
down_revision = '090498e10a94'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Fix timestamp fields (from string to proper datetime)
    # Add new timestamp columns with default value
    op.add_column('matchlog', sa.Column('created_at_new', sa.DateTime(),
                                      nullable=False,
                                      server_default=sa.func.now()))
    op.add_column('pendingquery', sa.Column('created_at_new', sa.DateTime(),
                                          nullable=False,
                                          server_default=sa.func.now()))

    # Drop old string columns
    op.drop_column('matchlog', 'created_at')
    op.drop_column('pendingquery', 'created_at')

    # Rename new columns to replace old ones
    op.alter_column('matchlog', 'created_at_new', new_column_name='created_at')
    op.alter_column('pendingquery', 'created_at_new', new_column_name='created_at')

    # Step 2: Add threshold column to pendingquery
    op.add_column('pendingquery', sa.Column('threshold', sa.Float(), nullable=False, server_default='0.9'))

    # Step 3: Add backend column to matchlog and remove language column
    op.add_column('matchlog', sa.Column('backend', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False, server_default='mock'))
    op.drop_column('matchlog', 'language')


def downgrade():
    # Reverse Step 3: Remove backend and add back language
    op.add_column('matchlog', sa.Column('language', sa.VARCHAR(length=10), autoincrement=False, nullable=False))
    op.drop_column('matchlog', 'backend')

    # Reverse Step 2: Remove threshold
    op.drop_column('pendingquery', 'threshold')

    # Reverse Step 1: Convert timestamp back to string - this is destructive
    # Add string columns with UUID default
    op.add_column('matchlog', sa.Column('created_at_new', sa.String(), nullable=False,
                                      server_default=sa.text('gen_random_uuid()::text')))
    op.add_column('pendingquery', sa.Column('created_at_new', sa.String(), nullable=False,
                                          server_default=sa.text('gen_random_uuid()::text')))

    # Drop timestamp columns
    op.drop_column('matchlog', 'created_at')
    op.drop_column('pendingquery', 'created_at')

    # Rename string columns
    op.alter_column('matchlog', 'created_at_new', new_column_name='created_at')
    op.alter_column('pendingquery', 'created_at_new', new_column_name='created_at')
