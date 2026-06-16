"""add unique constraint on telegram_user_id per user

Revision ID: a1b2c3d4e5f6
Revises: 9e4cd91fc9dc
Create Date: 2026-06-16 15:40:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9e4cd91fc9dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add index on telegram_user_id for fast lookup
    op.create_index(
        'ix_telegram_accounts_telegram_user_id',
        'telegram_accounts',
        ['telegram_user_id'],
    )
    # Add unique constraint: one telegram_user_id per platform user
    # NULLs are allowed (pending accounts) and don't violate uniqueness in PostgreSQL
    op.create_unique_constraint(
        'uq_telegram_accounts_user_tgid',
        'telegram_accounts',
        ['user_id', 'telegram_user_id'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_telegram_accounts_user_tgid', 'telegram_accounts', type_='unique')
    op.drop_index('ix_telegram_accounts_telegram_user_id', table_name='telegram_accounts')
