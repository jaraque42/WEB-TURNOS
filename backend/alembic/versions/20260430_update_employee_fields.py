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
    # 1. Añadir full_name y migrar datos
    with op.batch_alter_table("employees") as batch_op:
        batch_op.add_column(sa.Column("full_name", sa.String(length=200), nullable=True))
    
    op.execute(
        """
        UPDATE employees
        SET full_name = NULLIF(
            BTRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')),
            ''
        )
        """
    )
    op.execute("UPDATE employees SET full_name = 'Sin nombre' WHERE full_name IS NULL")
    
    # 2. Hacer full_name no nulo y eliminar columnas viejas
    with op.batch_alter_table("employees") as batch_op:
        batch_op.alter_column("full_name", nullable=False)
        batch_op.drop_column("first_name")
        batch_op.drop_column("last_name")
        batch_op.drop_column("address")

def downgrade() -> None:
    with op.batch_alter_table("employees") as batch_op:
        batch_op.add_column(sa.Column("first_name", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("last_name", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("address", sa.String(length=255), nullable=True))
        batch_op.drop_column("full_name")
