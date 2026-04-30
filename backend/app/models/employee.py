import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, Sequence, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
import enum


# Secuencia para auto-generar el ID de empleado
employee_id_seq = Sequence("employee_id_seq", start=1, increment=1)


# ─── Enums ──────────────────────────────────────────────
class EmployeeStatus(str, enum.Enum):
    ACTIVE = "activo"
    INACTIVE = "inactivo"
    ON_LEAVE = "licencia"
    SUSPENDED = "suspendido"


class LicenseType(str, enum.Enum):
    VACATION = "vacaciones"
    SICK = "enfermedad"
    MATERNITY = "maternidad"
    PATERNITY = "paternidad"
    STUDY = "estudio"
    PERSONAL = "personal"
    UNPAID = "sin_goce"
    OTHER = "otro"


class LicenseStatus(str, enum.Enum):
    PENDING = "pendiente"
    APPROVED = "aprobada"
    REJECTED = "rechazada"
    CANCELLED = "cancelada"


# ─── Categoría de Empleado ──────────────────────────────
class EmployeeCategory(Base):
    __tablename__ = "employee_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)  # ej: "Oficial", "Suboficial"
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    employees = relationship("Employee", back_populates="category")


# ─── Tipo de Agente ─────────────────────────────────────
class AgentType(Base):
    __tablename__ = "agent_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)  # ej: "Patrullero", "Despachante"
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    employees = relationship("Employee", back_populates="agent_type")


# ─── Empleado ───────────────────────────────────────────
class Employee(Base):
    __tablename__ = "employees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_number = Column(
        Integer, employee_id_seq, server_default=employee_id_seq.next_value(),
        unique=True, nullable=False, index=True,
    )
    full_name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=True)
    document_number = Column(String(30), unique=True, nullable=False, index=True)
    phone = Column(String(30), nullable=True)
    location = Column(String(150), nullable=True)
    hire_date = Column(Date, nullable=False)
    status = Column(
        Enum(EmployeeStatus, name="employee_status_enum"),
        default=EmployeeStatus.ACTIVE,
        nullable=False,
    )

    # Relaciones
    category_id = Column(UUID(as_uuid=True), ForeignKey("employee_categories.id"), nullable=True)
    agent_type_id = Column(UUID(as_uuid=True), ForeignKey("agent_types.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    category = relationship("EmployeeCategory", back_populates="employees")
    agent_type = relationship("AgentType", back_populates="employees")
    user = relationship("User", backref="employee", uselist=False)
    licenses = relationship("License", back_populates="employee", cascade="all, delete-orphan")


# ─── Licencia ───────────────────────────────────────────
class License(Base):
    __tablename__ = "licenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    license_type = Column(
        Enum(LicenseType, name="license_type_enum"),
        nullable=False,
    )
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(
        Enum(LicenseStatus, name="license_status_enum"),
        default=LicenseStatus.PENDING,
        nullable=False,
    )

    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    employee = relationship("Employee", back_populates="licenses")
