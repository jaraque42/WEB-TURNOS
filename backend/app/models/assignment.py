import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Date, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


# ─── Enums ──────────────────────────────────────────────
class AssignmentStatus(str, enum.Enum):
    ASSIGNED = "asignado"
    CONFIRMED = "confirmado"
    COMPLETED = "completado"
    CANCELLED = "cancelado"
    SWAPPED = "permutado"


class SwapRequestStatus(str, enum.Enum):
    PENDING = "pendiente"
    APPROVED = "aprobado"
    REJECTED = "rechazado"
    CANCELLED = "cancelado"


# ─── Asignación de Turno ───────────────────────────────
class ShiftAssignment(Base):
    """Asignación concreta de un empleado a un turno en una fecha."""
    __tablename__ = "shift_assignments"
    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="uq_employee_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(Date, nullable=False, index=True)
    status = Column(
        Enum(AssignmentStatus, name="assignment_status_enum"),
        default=AssignmentStatus.ASSIGNED,
        nullable=False,
    )
    notes = Column(Text, nullable=True)
    location = Column(String(150), nullable=True)

    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True)
    shift_type_id = Column(UUID(as_uuid=True), ForeignKey("shift_types.id"), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    employee = relationship("Employee", backref="assignments")
    shift_type = relationship("ShiftType", backref="assignments")


# ─── Solicitud de Permuta ──────────────────────────────
class SwapRequest(Base):
    """Solicitud de intercambio de turno entre dos empleados."""
    __tablename__ = "swap_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(
        Enum(SwapRequestStatus, name="swap_request_status_enum"),
        default=SwapRequestStatus.PENDING,
        nullable=False,
    )
    reason = Column(Text, nullable=True)

    # Asignación que el solicitante quiere ceder
    requester_assignment_id = Column(
        UUID(as_uuid=True), ForeignKey("shift_assignments.id"), nullable=False
    )
    # Asignación que el solicitante quiere recibir
    target_assignment_id = Column(
        UUID(as_uuid=True), ForeignKey("shift_assignments.id"), nullable=False
    )

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    requester_assignment = relationship(
        "ShiftAssignment", foreign_keys=[requester_assignment_id], backref="swap_requests_as_requester"
    )
    target_assignment = relationship(
        "ShiftAssignment", foreign_keys=[target_assignment_id], backref="swap_requests_as_target"
    )
