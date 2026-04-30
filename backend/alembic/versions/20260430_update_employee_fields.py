"""update employee fields

Revision ID: 20260430_update_employee_fields
Revises: 20260219_add_employee_location
Create Date: 2026-04-30 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260430_update_employee_fields"
down_revision = "20260219_add_employee_location"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Añadir full_name
    op.add_column("employees", sa.Column("full_name", sa.String(length=200), nullable=True))
    
    # 2. Migrar datos
    op.execute("UPDATE employees SET full_name = first_name || ' ' || last_name")
    
    # 3. Hacer full_name no nulo
    op.alter_column("employees", "full_name", nullable=False)

    # 4. Eliminar columnas viejas
    op.drop_column("employees", "first_name")
    op.drop_column("employees", "last_name")
    op.drop_column("employees", "address")

def downgrade() -> None:
    op.add_column("employees", sa.Column("first_name", sa.String(length=100), nullable=True))
    op.add_column("employees", sa.Column("last_name", sa.String(length=100), nullable=True))
    op.add_column("employees", sa.Column("address", sa.String(length=255), nullable=True))
    
    op.drop_column("employees", "full_name")
