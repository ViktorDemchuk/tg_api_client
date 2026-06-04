"""set_user_is_active_default_to_false

Revision ID: 9e4cd91fc9dc
Revises: 5534f89d2490
Create Date: 2026-06-01 20:49:59.005660

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e4cd91fc9dc'
down_revision: Union[str, None] = '5534f89d2490'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'is_active',
               existing_type=sa.Boolean(),
               server_default=sa.text('false'),
               existing_nullable=False)


def downgrade() -> None:
    op.alter_column('users', 'is_active',
               existing_type=sa.Boolean(),
               server_default=sa.text('true'),
               existing_nullable=False)
