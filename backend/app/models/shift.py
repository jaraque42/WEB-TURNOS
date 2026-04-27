import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, Time,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ShiftType(Base):
    """Tipo de turno (ej: mañana, tarde, noche, franco)."""
    __tablename__ = "shift_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)          # "Mañana", "Tarde", "Noche"
    code = Column(String(20), unique=True, nullable=False)           # "M", "T", "N", "F"
    description = Column(Text, nullable=True)
    start_time = Column(Time, nullable=False)                        # 06:00
    end_time = Column(Time, nullable=False)                          # 14:00
    duration_hours = Column(Integer, nullable=False)                  # 8
    color = Column(String(7), nullable=True)                          # "#FF5733" para UI
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    coverage_requirements = relationship("CoverageRequirement", back_populates="shift_type")


class CoverageRequirement(Base):
    """Cantidad de empleados necesarios para un turno en una fecha y ubicación."""
    __tablename__ = "coverage_requirements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(Date, nullable=False, index=True)
    min_employees = Column(Integer, nullable=False, default=1)
    max_employees = Column(Integer, nullable=True)
    location = Column(String(150), nullable=True)                    # "Sede Central", "Punto A"

    shift_type_id = Column(UUID(as_uuid=True), ForeignKey("shift_types.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    shift_type = relationship("ShiftType", back_populates="coverage_requirements")
