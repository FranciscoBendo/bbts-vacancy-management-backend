"""candidate rejection fields

Revision ID: 005
Revises: 004
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Cria o tipo ENUM explicitamente no PostgreSQL
    suggestion_status_enum = postgresql.ENUM('ACTIVE', 'REJECTED', name='suggestionstatus')
    suggestion_status_enum.create(op.get_bind())

    # 2. Adiciona a coluna status com o tipo criado
    op.add_column("candidate_suggestions", sa.Column("status", suggestion_status_enum, nullable=False, server_default="ACTIVE"))
    
    # 3. Adiciona as colunas de rejeição que faltavam
    op.add_column("candidate_suggestions", sa.Column("rejection_reason", sa.Text(), nullable=True))
    op.add_column("candidate_suggestions", sa.Column("rejected_at", sa.DateTime(), nullable=True))
    op.add_column("candidate_suggestions", sa.Column("rejected_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))

def downgrade():
    # Desfaz as alterações na ordem inversa
    op.drop_column("candidate_suggestions", "rejected_by_id")
    op.drop_column("candidate_suggestions", "rejected_at")
    op.drop_column("candidate_suggestions", "rejection_reason")
    op.drop_column("candidate_suggestions", "status")
    
    suggestion_status_enum = postgresql.ENUM('ACTIVE', 'REJECTED', name='suggestionstatus')
    suggestion_status_enum.drop(op.get_bind())