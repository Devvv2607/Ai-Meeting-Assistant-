"""add_error_message_to_live_session

Revision ID: 194b8960ce46
Revises: ea3b3c0e2349
Create Date: 2026-04-24 19:55:25.756236

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '194b8960ce46'
down_revision: Union[str, Sequence[str], None] = 'ea3b3c0e2349'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add error_message column to live_sessions table
    op.add_column('live_sessions', sa.Column('error_message', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove error_message column from live_sessions table
    op.drop_column('live_sessions', 'error_message')
