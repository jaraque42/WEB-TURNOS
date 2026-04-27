from datetime import date, datetime, time
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ─── Tipo de Turno ──────────────────────────────────────

class ShiftTypeBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=20)
    description: Optional[str] = None
    start_time: time
    end_time: time
    duration_hours: int = Field(..., ge=1, le=24)
    color: Optional[str] = Field(None, max_length=7, pattern=r"^#[0-9A-Fa-f]{6}$")


class ShiftTypeCreate(ShiftTypeBase):
    pass


class ShiftTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    duration_hours: Optional[int] = Field(None, ge=1, le=24)
    color: Optional[str] = Field(None, max_length=7, pattern=r"^#[0-9A-Fa-f]{6}$")
    is_active: Optional[bool] = None


class ShiftTypeOut(ShiftTypeBase):
    id: UUID
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Cobertura ──────────────────────────────────────────

class CoverageRequirementBase(BaseModel):
    date: date
    min_employees: int = Field(..., ge=1)
    max_employees: Optional[int] = Field(None, ge=1)
    location: Optional[str] = Field(None, max_length=150)


class CoverageRequirementCreate(CoverageRequirementBase):
    shift_type_id: UUID


class CoverageRequirementUpdate(BaseModel):
    date: Optional[date] = None
    min_employees: Optional[int] = Field(None, ge=1)
    max_employees: Optional[int] = Field(None, ge=1)
    location: Optional[str] = Field(None, max_length=150)
    shift_type_id: Optional[UUID] = None


class CoverageRequirementOut(CoverageRequirementBase):
    id: UUID
    shift_type_id: UUID
    shift_type: Optional[ShiftTypeOut] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Bulk / Generación ──────────────────────────────────

class CoverageBulkCreate(BaseModel):
    """Crear coberturas para un rango de fechas y múltiples turnos."""
    start_date: date
    end_date: date
    shift_type_ids: List[UUID]
    min_employees: int = Field(..., ge=1)
    max_employees: Optional[int] = Field(None, ge=1)
    location: Optional[str] = Field(None, max_length=150)
