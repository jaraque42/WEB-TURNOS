"""add employee location

Revision ID: 20260219_add_employee_location
Revises: 
Create Date: 2026-02-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260219_add_employee_location"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("location", sa.String(length=150), nullable=True))


def downgrade() -> None:
    op.drop_column("employees", "location")
