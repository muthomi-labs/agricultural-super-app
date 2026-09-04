"""add user language preference

Revision ID: b4c5d6e7f8a9
Revises: e3f4a5b6c7d8
Create Date: 2026-09-04 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4c5d6e7f8a9'
down_revision = 'e3f4a5b6c7d8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'users',
        sa.Column('language', sa.String(length=5), nullable=False, server_default='en'),
    )


def downgrade():
    op.drop_column('users', 'language')
