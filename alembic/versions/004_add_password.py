"""add password_hash to users
Revision ID: 004
Revises: 003
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))

def downgrade():
    op.drop_column("users", "password_hash")
