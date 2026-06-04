"""set_telegram_account_is_active_default_to_false

Revision ID: 5534f89d2490
Revises: 0001
Create Date: 2026-06-01 20:42:03.189417

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5534f89d2490'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('telegram_accounts', 'is_active',
               existing_type=sa.Boolean(),
               server_default=sa.text('false'),
               existing_nullable=False)


def downgrade() -> None:
    op.alter_column('telegram_accounts', 'is_active',
               existing_type=sa.Boolean(),
               server_default=sa.text('true'),
               existing_nullable=False)
