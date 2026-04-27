from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.shift import (
    ShiftTypeCreate, ShiftTypeOut, ShiftTypeUpdate,
    CoverageRequirementCreate, CoverageRequirementOut, CoverageRequirementUpdate,
    CoverageBulkCreate,
)
from app.services.auth import get_current_user, require_permission
from app.services import shift as shift_service

router = APIRouter(tags=["Turnos"])


# ═══════════════════════════════════════════════════════════
#  Tipos de Turno
# ═══════════════════════════════════════════════════════════

@router.get("/shift-types/", response_model=List[ShiftTypeOut])
async def list_shift_types(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = Query(False, description="Solo tipos de turno activos"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("shifts:read")),
):
    """Listar tipos de turno."""
    return await shift_service.get_shift_types(db, skip, limit, active_only)


@router.post("/shift-types/", response_model=ShiftTypeOut, status_code=201)
async def create_shift_type(
    data: ShiftTypeCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("shifts:create")),
):
    """Crear un tipo de turno."""
    return await shift_service.create_shift_type(db, data)


@router.get("/shift-types/{shift_type_id}", response_model=ShiftTypeOut)
async def get_shift_type(
    shift_type_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("shifts:read")),
):
    """Obtener un tipo de turno por ID."""
    return await shift_service.get_shift_type_by_id(db, shift_type_id)


@router.patch("/shift-types/{shift_type_id}", response_model=ShiftTypeOut)
async def update_shift_type(
    shift_type_id: UUID,
    data: ShiftTypeUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("shifts:update")),
):
    """Actualizar un tipo de turno."""
    return await shift_service.update_shift_type(db, shift_type_id, data)


@router.delete("/shift-types/{shift_type_id}", status_code=204)
async def delete_shift_type(
    shift_type_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("shifts:delete")),
):
    """Eliminar un tipo de turno. Falla si tiene coberturas asociadas."""
    await shift_service.delete_shift_type(db, shift_type_id)


# ═══════════════════════════════════════════════════════════
#  Requerimientos de Cobertura
# ═══════════════════════════════════════════════════════════

@router.get("/coverage/", response_model=List[CoverageRequirementOut])
async def list_coverage_requirements(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[date] = Query(None, description="Fecha desde"),
    end_date: Optional[date] = Query(None, description="Fecha hasta"),
    shift_type_id: Optional[UUID] = Query(None),
    location: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("shifts:read")),
):
    """Listar requerimientos de cobertura con filtros opcionales."""
    return await shift_service.get_coverage_requirements(
        db, skip, limit, start_date, end_date, shift_type_id, location,
    )


@router.post("/coverage/", response_model=CoverageRequirementOut, status_code=201)
async def create_coverage_requirement(
    data: CoverageRequirementCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("shifts:create")),
):
    """Crear un requerimiento de cobertura individual."""
    return await shift_service.create_coverage(db, data)


@router.post("/coverage/bulk/", response_model=List[CoverageRequirementOut], status_code=201)
async def bulk_create_coverage(
    data: CoverageBulkCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("shifts:create")),
):
    """Crear coberturas en lote para un rango de fechas y múltiples tipos de turno."""
    return await shift_service.bulk_create_coverage(db, data)


@router.get("/coverage/{coverage_id}", response_model=CoverageRequirementOut)
async def get_coverage_requirement(
    coverage_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("shifts:read")),
):
    """Obtener un requerimiento de cobertura por ID."""
    return await shift_service.get_coverage_by_id(db, coverage_id)


@router.patch("/coverage/{coverage_id}", response_model=CoverageRequirementOut)
async def update_coverage_requirement(
    coverage_id: UUID,
    data: CoverageRequirementUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("shifts:update")),
):
    """Actualizar un requerimiento de cobertura."""
    return await shift_service.update_coverage(db, coverage_id, data)


@router.delete("/coverage/{coverage_id}", status_code=204)
async def delete_coverage_requirement(
    coverage_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("shifts:delete")),
):
    """Eliminar un requerimiento de cobertura."""
    await shift_service.delete_coverage(db, coverage_id)
