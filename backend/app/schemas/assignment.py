from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.assignment import AssignmentStatus, SwapRequestStatus


# ─── Asignación de Turno ───────────────────────────────

class ShiftAssignmentBase(BaseModel):
    date: date
    employee_id: UUID
    shift_type_id: UUID
    notes: Optional[str] = None
    location: Optional[str] = Field(None, max_length=150)


class ShiftAssignmentCreate(ShiftAssignmentBase):
    pass


class ShiftAssignmentUpdate(BaseModel):
    date: Optional[date] = None
    employee_id: Optional[UUID] = None
    shift_type_id: Optional[UUID] = None
    status: Optional[AssignmentStatus] = None
    notes: Optional[str] = None
    location: Optional[str] = Field(None, max_length=150)


class ShiftAssignmentOut(ShiftAssignmentBase):
    id: UUID
    status: AssignmentStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Datos expandidos opcionales
    employee_name: Optional[str] = None
    shift_type_name: Optional[str] = None
    shift_type_code: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Generación masiva de asignaciones ─────────────────

class BulkAssignmentCreate(BaseModel):
    """Generar asignaciones para un rango de fechas."""
    start_date: date
    end_date: date
    employee_ids: List[UUID]
    shift_type_id: UUID
    location: Optional[str] = Field(None, max_length=150)


class BulkAssignmentResult(BaseModel):
    created: int
    skipped: int
    details: List[str] = []


class BulkDeleteRequest(BaseModel):
    """IDs de asignaciones a eliminar en lote."""
    assignment_ids: List[UUID]


class BulkDeleteResult(BaseModel):
    deleted: int
    skipped: int
    details: List[str] = []


# ─── Solicitud de Permuta ──────────────────────────────

class SwapRequestCreate(BaseModel):
    requester_assignment_id: UUID
    target_assignment_id: UUID
    reason: Optional[str] = None


class SwapRequestUpdate(BaseModel):
    status: SwapRequestStatus
    reason: Optional[str] = None


class SwapRequestOut(BaseModel):
    id: UUID
    status: SwapRequestStatus
    reason: Optional[str] = None
    requester_assignment_id: UUID
    target_assignment_id: UUID
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Estadísticas ──────────────────────────────────────

class AssignmentStats(BaseModel):
    """Resumen de asignaciones para un período."""
    total_assignments: int
    by_status: dict[str, int]
    by_shift_type: dict[str, int]
    employees_assigned: int
