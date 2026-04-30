from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.assignment import AssignmentStatus, SwapRequestStatus
from app.models.user import User
from app.schemas.assignment import (
    ShiftAssignmentCreate, ShiftAssignmentOut, ShiftAssignmentUpdate,
    BulkAssignmentCreate, BulkAssignmentResult,
    BulkDeleteRequest, BulkDeleteResult,
    SwapRequestCreate, SwapRequestOut, SwapRequestUpdate,
    AssignmentStats,
)
from app.services.auth import get_current_user, require_permission
from app.services import assignment as assignment_service

router = APIRouter(tags=["Asignaciones"])


# ═══════════════════════════════════════════════════════════
#  Asignaciones
# ═══════════════════════════════════════════════════════════

def _enrich_assignment(a) -> dict:
    """Agrega campos expandidos (employee_name, shift_type_name, etc.)."""
    data = {
        "id": a.id,
        "date": a.date,
        "employee_id": a.employee_id,
        "shift_type_id": a.shift_type_id,
        "status": a.status,
        "notes": a.notes,
        "location": a.location,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
        "employee_name": None,
        "shift_type_name": None,
        "shift_type_code": None,
    }
    if a.employee:
        data["employee_name"] = a.employee.full_name if a.employee else None
    if a.shift_type:
        data["shift_type_name"] = a.shift_type.name
        data["shift_type_code"] = a.shift_type.code
    return data


@router.get("/assignments/", response_model=List[ShiftAssignmentOut])
async def list_assignments(
    skip: int = 0,
    limit: int = 100,
    date_from: Optional[date] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    employee_id: Optional[UUID] = Query(None),
    shift_type_id: Optional[UUID] = Query(None),
    status: Optional[AssignmentStatus] = Query(None, alias="assignment_status"),
    location: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("assignments:read")),
):
    """Listar asignaciones con filtros opcionales."""
    assignments = await assignment_service.get_assignments(
        db, skip, limit, date_from, date_to, employee_id,
        shift_type_id, status, location,
    )
    return [_enrich_assignment(a) for a in assignments]


@router.post("/assignments/", response_model=ShiftAssignmentOut, status_code=201)
async def create_assignment(
    data: ShiftAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("assignments:create")),
):
    """Crear una asignación de turno con validaciones de negocio."""
    a = await assignment_service.create_assignment(db, data)
    return _enrich_assignment(a)


@router.get("/assignments/stats", response_model=AssignmentStats)
async def assignment_stats(
    date_from: date = Query(..., description="Fecha inicio"),
    date_to: date = Query(..., description="Fecha fin"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("assignments:read")),
):
    """Obtener estadísticas de asignaciones para un rango de fechas."""
    return await assignment_service.get_assignment_stats(db, date_from, date_to)


@router.get("/assignments/{assignment_id}", response_model=ShiftAssignmentOut)
async def get_assignment(
    assignment_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("assignments:read")),
):
    """Obtener una asignación por ID."""
    a = await assignment_service.get_assignment_by_id(db, assignment_id)
    return _enrich_assignment(a)


@router.patch("/assignments/{assignment_id}", response_model=ShiftAssignmentOut)
async def update_assignment(
    assignment_id: UUID,
    data: ShiftAssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("assignments:update")),
):
    """Actualizar una asignación (incluye cambio de estado)."""
    a = await assignment_service.update_assignment(db, assignment_id, data)
    return _enrich_assignment(a)


@router.delete("/assignments/{assignment_id}", status_code=204)
async def delete_assignment(
    assignment_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("assignments:delete")),
):
    """Eliminar una asignación (no se puede si está completada)."""
    await assignment_service.delete_assignment(db, assignment_id)


@router.post("/assignments/bulk", response_model=BulkAssignmentResult, status_code=201)
async def bulk_create_assignments(
    data: BulkAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("assignments:create")),
):
    """Generar asignaciones masivas para un rango de fechas y empleados."""
    return await assignment_service.bulk_create_assignments(db, data)


@router.post("/assignments/bulk-delete", response_model=BulkDeleteResult)
async def bulk_delete_assignments(
    data: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("assignments:delete")),
):
    """Eliminar múltiples asignaciones de golpe."""
    return await assignment_service.bulk_delete_assignments(db, data.assignment_ids)


# ═══════════════════════════════════════════════════════════
#  Permutas
# ═══════════════════════════════════════════════════════════

@router.get("/swap-requests/", response_model=List[SwapRequestOut])
async def list_swap_requests(
    skip: int = 0,
    limit: int = 50,
    status: Optional[SwapRequestStatus] = Query(None, alias="swap_status"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("assignments:read")),
):
    """Listar solicitudes de permuta."""
    return await assignment_service.get_swap_requests(db, skip, limit, status)


@router.post("/swap-requests/", response_model=SwapRequestOut, status_code=201)
async def create_swap_request(
    data: SwapRequestCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("assignments:create")),
):
    """Crear una solicitud de permuta entre dos asignaciones."""
    return await assignment_service.create_swap_request(db, data)


@router.patch("/swap-requests/{swap_id}", response_model=SwapRequestOut)
async def resolve_swap_request(
    swap_id: UUID,
    data: SwapRequestUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("assignments:update")),
):
    """Aprobar o rechazar una solicitud de permuta."""
    return await assignment_service.resolve_swap_request(db, swap_id, data)
