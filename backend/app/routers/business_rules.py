from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.business_rule import RuleCategory
from app.models.user import User
from app.schemas.business_rule import (
    BusinessRuleCreate, BusinessRuleOut, BusinessRuleUpdate,
    ShiftIncompatibilityCreate, ShiftIncompatibilityOut, ShiftIncompatibilityUpdate,
    AssignmentValidationRequest, AssignmentValidationResult,
)
from app.services.auth import get_current_user, require_permission
from app.services import business_rule as rule_service

router = APIRouter(tags=["Reglas de Negocio"])


# ═══════════════════════════════════════════════════════════
#  Reglas de Negocio
# ═══════════════════════════════════════════════════════════

@router.get("/business-rules/", response_model=List[BusinessRuleOut])
async def list_business_rules(
    skip: int = 0,
    limit: int = 100,
    category: Optional[RuleCategory] = Query(None),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("rules:read")),
):
    """Listar reglas de negocio con filtros opcionales."""
    return await rule_service.get_business_rules(db, skip, limit, category, active_only)


@router.post("/business-rules/", response_model=BusinessRuleOut, status_code=201)
async def create_business_rule(
    data: BusinessRuleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("rules:manage")),
):
    """Crear una regla de negocio."""
    return await rule_service.create_business_rule(db, data)


@router.get("/business-rules/{rule_id}", response_model=BusinessRuleOut)
async def get_business_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("rules:read")),
):
    """Obtener una regla por ID."""
    return await rule_service.get_business_rule_by_id(db, rule_id)


@router.patch("/business-rules/{rule_id}", response_model=BusinessRuleOut)
async def update_business_rule(
    rule_id: UUID,
    data: BusinessRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("rules:manage")),
):
    """Actualizar una regla de negocio."""
    return await rule_service.update_business_rule(db, rule_id, data)


@router.delete("/business-rules/{rule_id}", status_code=204)
async def delete_business_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("rules:manage")),
):
    """Eliminar una regla de negocio."""
    await rule_service.delete_business_rule(db, rule_id)


# ═══════════════════════════════════════════════════════════
#  Incompatibilidades de Turnos
# ═══════════════════════════════════════════════════════════

def _enrich_incompatibility(inc) -> dict:
    data = {
        "id": inc.id,
        "shift_type_a_id": inc.shift_type_a_id,
        "shift_type_b_id": inc.shift_type_b_id,
        "direction": inc.direction,
        "description": inc.description,
        "is_active": inc.is_active,
        "created_at": inc.created_at,
        "shift_type_a_name": None,
        "shift_type_b_name": None,
    }
    if inc.shift_type_a:
        data["shift_type_a_name"] = inc.shift_type_a.name
    if inc.shift_type_b:
        data["shift_type_b_name"] = inc.shift_type_b.name
    return data


@router.get("/shift-incompatibilities/", response_model=List[ShiftIncompatibilityOut])
async def list_incompatibilities(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("rules:read")),
):
    """Listar incompatibilidades de turnos."""
    items = await rule_service.get_incompatibilities(db, skip, limit, active_only)
    return [_enrich_incompatibility(i) for i in items]


@router.post("/shift-incompatibilities/", response_model=ShiftIncompatibilityOut, status_code=201)
async def create_incompatibility(
    data: ShiftIncompatibilityCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("rules:manage")),
):
    """Crear una incompatibilidad entre tipos de turno."""
    inc = await rule_service.create_incompatibility(db, data)
    return _enrich_incompatibility(inc)


@router.get("/shift-incompatibilities/{inc_id}", response_model=ShiftIncompatibilityOut)
async def get_incompatibility(
    inc_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("rules:read")),
):
    """Obtener una incompatibilidad por ID."""
    inc = await rule_service.get_incompatibility_by_id(db, inc_id)
    return _enrich_incompatibility(inc)


@router.patch("/shift-incompatibilities/{inc_id}", response_model=ShiftIncompatibilityOut)
async def update_incompatibility(
    inc_id: UUID,
    data: ShiftIncompatibilityUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("rules:manage")),
):
    """Actualizar una incompatibilidad."""
    inc = await rule_service.update_incompatibility(db, inc_id, data)
    return _enrich_incompatibility(inc)


@router.delete("/shift-incompatibilities/{inc_id}", status_code=204)
async def delete_incompatibility(
    inc_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("rules:manage")),
):
    """Eliminar una incompatibilidad."""
    await rule_service.delete_incompatibility(db, inc_id)


# ═══════════════════════════════════════════════════════════
#  Validación previa
# ═══════════════════════════════════════════════════════════

@router.post("/assignments/validate", response_model=AssignmentValidationResult)
async def validate_assignment(
    data: AssignmentValidationRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("assignments:read")),
):
    """
    Validar una asignación contra todas las reglas de negocio
    sin crearla. Útil para previsualización en el frontend.
    """
    from datetime import date as date_type
    target_date = date_type.fromisoformat(data.date)

    errors, warnings = await rule_service.validate_assignment_rules(
        db, data.employee_id, data.shift_type_id, target_date
    )

    return AssignmentValidationResult(
        is_valid=len(errors) == 0,
        violations=errors,
        warnings=warnings,
    )
