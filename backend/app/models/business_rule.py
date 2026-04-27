import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


# ─── Enums ──────────────────────────────────────────────
class RuleCategory(str, enum.Enum):
    HOURS = "horas"                          # Límites de horas
    CONSECUTIVE = "dias_consecutivos"        # Días consecutivos máximos
    REST = "descanso"                        # Descanso mínimo entre turnos
    INCOMPATIBILITY = "incompatibilidad"     # Turnos incompatibles consecutivos
    WEEKLY_REST = "descanso_semanal"         # Franco semanal obligatorio


class IncompatibilityDirection(str, enum.Enum):
    """Dirección de la incompatibilidad: A no puede ir seguido de B."""
    FORWARD = "siguiente"    # shift_type_a → shift_type_b prohibido
    BACKWARD = "anterior"    # shift_type_b → shift_type_a prohibido
    BOTH = "ambos"           # ninguno de los dos órdenes


# ─── Regla de Negocio ──────────────────────────────────
class BusinessRule(Base):
    """Regla de negocio configurable para validar asignaciones."""
    __tablename__ = "business_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(150), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(
        Enum(RuleCategory, name="rule_category_enum"),
        nullable=False,
    )
    is_active = Column(Boolean, default=True, nullable=False)

    # Valores configurables según categoría:
    # HOURS → max_value = horas semanales máximas (ej: 48)
    # CONSECUTIVE → max_value = días consecutivos máximos (ej: 6)
    # REST → max_value = horas mínimas de descanso (ej: 12)
    # WEEKLY_REST → max_value = francos mínimos por semana (ej: 1)
    max_value = Column(Integer, nullable=False)

    # Para reglas por categoría de empleado (nullable = aplica a todos)
    employee_category_id = Column(
        UUID(as_uuid=True), ForeignKey("employee_categories.id"), nullable=True
    )

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    employee_category = relationship("EmployeeCategory", backref="business_rules")


# ─── Incompatibilidad de Turnos ────────────────────────
class ShiftIncompatibility(Base):
    """Define pares de turnos que no pueden asignarse consecutivamente."""
    __tablename__ = "shift_incompatibilities"
    __table_args__ = (
        UniqueConstraint(
            "shift_type_a_id", "shift_type_b_id",
            name="uq_shift_incompatibility_pair",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    direction = Column(
        Enum(IncompatibilityDirection, name="incompatibility_direction_enum"),
        default=IncompatibilityDirection.FORWARD,
        nullable=False,
    )
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    shift_type_a_id = Column(
        UUID(as_uuid=True), ForeignKey("shift_types.id"), nullable=False
    )
    shift_type_b_id = Column(
        UUID(as_uuid=True), ForeignKey("shift_types.id"), nullable=False
    )

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    shift_type_a = relationship("ShiftType", foreign_keys=[shift_type_a_id], backref="incompatibilities_as_a")
    shift_type_b = relationship("ShiftType", foreign_keys=[shift_type_b_id], backref="incompatibilities_as_b")
