"""Servicio de reglas de negocio: CRUD + motor de validación."""
from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.business_rule import (
    BusinessRule, RuleCategory,
    ShiftIncompatibility, IncompatibilityDirection,
)
from app.models.assignment import ShiftAssignment, AssignmentStatus
from app.models.employee import Employee
from app.models.shift import ShiftType
from app.schemas.business_rule import (
    BusinessRuleCreate, BusinessRuleUpdate,
    ShiftIncompatibilityCreate, ShiftIncompatibilityUpdate,
    RuleViolation,
)


# ═══════════════════════════════════════════════════════════
#  CRUD – Reglas de Negocio
# ═══════════════════════════════════════════════════════════

async def get_business_rules(
    db: AsyncSession, skip: int = 0, limit: int = 100,
    category: RuleCategory | None = None, active_only: bool = False,
) -> List[BusinessRule]:
    query = select(BusinessRule)
    if category:
        query = query.where(BusinessRule.category == category)
    if active_only:
        query = query.where(BusinessRule.is_active == True)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


async def get_business_rule_by_id(db: AsyncSession, rule_id: UUID) -> BusinessRule:
    result = await db.execute(select(BusinessRule).where(BusinessRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Regla de negocio no encontrada")
    return rule


async def create_business_rule(db: AsyncSession, data: BusinessRuleCreate) -> BusinessRule:
    # Verificar nombre duplicado
    result = await db.execute(select(BusinessRule).where(BusinessRule.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Ya existe la regla '{data.name}'")

    rule = BusinessRule(**data.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def update_business_rule(
    db: AsyncSession, rule_id: UUID, data: BusinessRuleUpdate
) -> BusinessRule:
    rule = await get_business_rule_by_id(db, rule_id)
    update_fields = data.model_dump(exclude_unset=True)

    if "name" in update_fields and update_fields["name"] != rule.name:
        dup = await db.execute(
            select(BusinessRule).where(BusinessRule.name == update_fields["name"])
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Ya existe la regla '{update_fields['name']}'")

    for field, value in update_fields.items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return rule


async def delete_business_rule(db: AsyncSession, rule_id: UUID) -> None:
    rule = await get_business_rule_by_id(db, rule_id)
    await db.delete(rule)
    await db.commit()


# ═══════════════════════════════════════════════════════════
#  CRUD – Incompatibilidades de Turnos
# ═══════════════════════════════════════════════════════════

async def get_incompatibilities(
    db: AsyncSession, skip: int = 0, limit: int = 100, active_only: bool = False,
) -> List[ShiftIncompatibility]:
    query = select(ShiftIncompatibility).options(
        selectinload(ShiftIncompatibility.shift_type_a),
        selectinload(ShiftIncompatibility.shift_type_b),
    )
    if active_only:
        query = query.where(ShiftIncompatibility.is_active == True)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


async def get_incompatibility_by_id(db: AsyncSession, inc_id: UUID) -> ShiftIncompatibility:
    result = await db.execute(
        select(ShiftIncompatibility).options(
            selectinload(ShiftIncompatibility.shift_type_a),
            selectinload(ShiftIncompatibility.shift_type_b),
        ).where(ShiftIncompatibility.id == inc_id)
    )
    inc = result.scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=404, detail="Incompatibilidad no encontrada")
    return inc


async def create_incompatibility(
    db: AsyncSession, data: ShiftIncompatibilityCreate
) -> ShiftIncompatibility:
    if data.shift_type_a_id == data.shift_type_b_id:
        raise HTTPException(status_code=422, detail="Los tipos de turno deben ser diferentes")

    # Verificar que existan los shift types
    for st_id in (data.shift_type_a_id, data.shift_type_b_id):
        r = await db.execute(select(ShiftType).where(ShiftType.id == st_id))
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"Tipo de turno {st_id} no encontrado")

    # Verificar duplicado (A,B) o (B,A)
    result = await db.execute(
        select(ShiftIncompatibility).where(
            or_(
                and_(
                    ShiftIncompatibility.shift_type_a_id == data.shift_type_a_id,
                    ShiftIncompatibility.shift_type_b_id == data.shift_type_b_id,
                ),
                and_(
                    ShiftIncompatibility.shift_type_a_id == data.shift_type_b_id,
                    ShiftIncompatibility.shift_type_b_id == data.shift_type_a_id,
                ),
            )
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Esta incompatibilidad ya existe")

    inc = ShiftIncompatibility(**data.model_dump())
    db.add(inc)
    await db.commit()
    await db.refresh(inc, attribute_names=["shift_type_a", "shift_type_b"])
    return inc


async def update_incompatibility(
    db: AsyncSession, inc_id: UUID, data: ShiftIncompatibilityUpdate
) -> ShiftIncompatibility:
    inc = await get_incompatibility_by_id(db, inc_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(inc, field, value)
    await db.commit()
    await db.refresh(inc, attribute_names=["shift_type_a", "shift_type_b"])
    return inc


async def delete_incompatibility(db: AsyncSession, inc_id: UUID) -> None:
    inc = await get_incompatibility_by_id(db, inc_id)
    await db.delete(inc)
    await db.commit()


# ═══════════════════════════════════════════════════════════
#  Motor de Validación
# ═══════════════════════════════════════════════════════════

async def _get_active_rules(
    db: AsyncSession, category: RuleCategory, employee_category_id: UUID | None = None,
) -> List[BusinessRule]:
    """Obtiene reglas activas de una categoría, priorizando las específicas por categoría."""
    query = select(BusinessRule).where(
        and_(
            BusinessRule.category == category,
            BusinessRule.is_active == True,
            or_(
                BusinessRule.employee_category_id == None,
                BusinessRule.employee_category_id == employee_category_id,
            ),
        )
    )
    result = await db.execute(query)
    rules = result.scalars().all()

    # Si hay regla específica para la categoría del empleado, priorizar esa
    specific = [r for r in rules if r.employee_category_id is not None]
    return specific if specific else [r for r in rules if r.employee_category_id is None]


async def validate_max_weekly_hours(
    db: AsyncSession, employee_id: UUID, target_date: date,
    shift_type: ShiftType, employee_category_id: UUID | None,
    exclude_id: UUID | None = None,
) -> List[RuleViolation]:
    """Verifica que no se superen las horas semanales máximas."""
    violations = []
    rules = await _get_active_rules(db, RuleCategory.HOURS, employee_category_id)
    if not rules:
        return violations

    max_hours = rules[0].max_value
    rule_name = rules[0].name

    # Calcular semana (lunes a domingo)
    week_start = target_date - timedelta(days=target_date.weekday())
    week_end = week_start + timedelta(days=6)

    query = (
        select(func.coalesce(func.sum(ShiftType.duration_hours), 0))
        .select_from(ShiftAssignment)
        .join(ShiftType, ShiftAssignment.shift_type_id == ShiftType.id)
        .where(
            and_(
                ShiftAssignment.employee_id == employee_id,
                ShiftAssignment.date >= week_start,
                ShiftAssignment.date <= week_end,
                ShiftAssignment.status != AssignmentStatus.CANCELLED,
            )
        )
    )
    if exclude_id:
        query = query.where(ShiftAssignment.id != exclude_id)

    result = await db.execute(query)
    current_hours = result.scalar() or 0
    projected = current_hours + shift_type.duration_hours

    if projected > max_hours:
        violations.append(RuleViolation(
            rule_name=rule_name,
            category=RuleCategory.HOURS.value,
            detail=f"Se exceden las horas semanales: {projected}h proyectadas "
                   f"(máximo: {max_hours}h, actuales: {current_hours}h)",
        ))

    return violations


async def validate_consecutive_days(
    db: AsyncSession, employee_id: UUID, target_date: date,
    employee_category_id: UUID | None,
    exclude_id: UUID | None = None,
) -> List[RuleViolation]:
    """Verifica que no se superen los días consecutivos máximos."""
    violations = []
    rules = await _get_active_rules(db, RuleCategory.CONSECUTIVE, employee_category_id)
    if not rules:
        return violations

    max_days = rules[0].max_value
    rule_name = rules[0].name

    # Contar días consecutivos hacia atrás y adelante
    consecutive = 1  # el día propuesto

    # Hacia atrás
    check_date = target_date - timedelta(days=1)
    while True:
        query = select(ShiftAssignment).where(
            and_(
                ShiftAssignment.employee_id == employee_id,
                ShiftAssignment.date == check_date,
                ShiftAssignment.status != AssignmentStatus.CANCELLED,
            )
        )
        if exclude_id:
            query = query.where(ShiftAssignment.id != exclude_id)
        result = await db.execute(query)
        if result.scalar_one_or_none():
            consecutive += 1
            check_date -= timedelta(days=1)
        else:
            break

    # Hacia adelante
    check_date = target_date + timedelta(days=1)
    while True:
        query = select(ShiftAssignment).where(
            and_(
                ShiftAssignment.employee_id == employee_id,
                ShiftAssignment.date == check_date,
                ShiftAssignment.status != AssignmentStatus.CANCELLED,
            )
        )
        if exclude_id:
            query = query.where(ShiftAssignment.id != exclude_id)
        result = await db.execute(query)
        if result.scalar_one_or_none():
            consecutive += 1
            check_date += timedelta(days=1)
        else:
            break

    if consecutive > max_days:
        violations.append(RuleViolation(
            rule_name=rule_name,
            category=RuleCategory.CONSECUTIVE.value,
            detail=f"Se superan los días consecutivos: {consecutive} días "
                   f"(máximo permitido: {max_days})",
        ))

    return violations


async def validate_weekly_rest(
    db: AsyncSession, employee_id: UUID, target_date: date,
    employee_category_id: UUID | None,
    exclude_id: UUID | None = None,
) -> List[RuleViolation]:
    """Verifica que el empleado tenga al menos N francos por semana."""
    violations = []
    rules = await _get_active_rules(db, RuleCategory.WEEKLY_REST, employee_category_id)
    if not rules:
        return violations

    min_rest_days = rules[0].max_value  # max_value = mínimo de días libres
    rule_name = rules[0].name

    week_start = target_date - timedelta(days=target_date.weekday())
    week_end = week_start + timedelta(days=6)

    query = select(func.count(ShiftAssignment.id)).where(
        and_(
            ShiftAssignment.employee_id == employee_id,
            ShiftAssignment.date >= week_start,
            ShiftAssignment.date <= week_end,
            ShiftAssignment.status != AssignmentStatus.CANCELLED,
        )
    )
    if exclude_id:
        query = query.where(ShiftAssignment.id != exclude_id)

    result = await db.execute(query)
    work_days = (result.scalar() or 0) + 1  # +1 por la asignación propuesta
    free_days = 7 - work_days

    if free_days < min_rest_days:
        violations.append(RuleViolation(
            rule_name=rule_name,
            category=RuleCategory.WEEKLY_REST.value,
            detail=f"El empleado tendría solo {free_days} día(s) libre(s) esta semana "
                   f"(mínimo requerido: {min_rest_days})",
        ))

    return violations


async def validate_shift_incompatibilities(
    db: AsyncSession, employee_id: UUID, target_date: date,
    shift_type_id: UUID,
    exclude_id: UUID | None = None,
) -> List[RuleViolation]:
    """Verifica incompatibilidades con turnos adyacentes."""
    violations = []

    # Obtener incompatibilidades activas
    inc_result = await db.execute(
        select(ShiftIncompatibility).options(
            selectinload(ShiftIncompatibility.shift_type_a),
            selectinload(ShiftIncompatibility.shift_type_b),
        ).where(ShiftIncompatibility.is_active == True)
    )
    incompatibilities = inc_result.scalars().all()
    if not incompatibilities:
        return violations

    # Obtener asignaciones del día anterior y siguiente
    day_before = target_date - timedelta(days=1)
    day_after = target_date + timedelta(days=1)

    query = select(ShiftAssignment).options(selectinload(ShiftAssignment.shift_type)).where(
        and_(
            ShiftAssignment.employee_id == employee_id,
            ShiftAssignment.date.in_([day_before, day_after]),
            ShiftAssignment.status != AssignmentStatus.CANCELLED,
        )
    )
    if exclude_id:
        query = query.where(ShiftAssignment.id != exclude_id)

    result = await db.execute(query)
    adjacent = result.scalars().all()

    for adj in adjacent:
        for inc in incompatibilities:
            is_violation = False

            if adj.date == day_before:
                # El turno anterior (adj) → el turno propuesto (shift_type_id)
                if inc.direction in (IncompatibilityDirection.FORWARD, IncompatibilityDirection.BOTH):
                    if adj.shift_type_id == inc.shift_type_a_id and shift_type_id == inc.shift_type_b_id:
                        is_violation = True
                if inc.direction in (IncompatibilityDirection.BACKWARD, IncompatibilityDirection.BOTH):
                    if adj.shift_type_id == inc.shift_type_b_id and shift_type_id == inc.shift_type_a_id:
                        is_violation = True

            elif adj.date == day_after:
                # El turno propuesto (shift_type_id) → el turno siguiente (adj)
                if inc.direction in (IncompatibilityDirection.FORWARD, IncompatibilityDirection.BOTH):
                    if shift_type_id == inc.shift_type_a_id and adj.shift_type_id == inc.shift_type_b_id:
                        is_violation = True
                if inc.direction in (IncompatibilityDirection.BACKWARD, IncompatibilityDirection.BOTH):
                    if shift_type_id == inc.shift_type_b_id and adj.shift_type_id == inc.shift_type_a_id:
                        is_violation = True

            if is_violation:
                a_name = inc.shift_type_a.name if inc.shift_type_a else str(inc.shift_type_a_id)
                b_name = inc.shift_type_b.name if inc.shift_type_b else str(inc.shift_type_b_id)
                violations.append(RuleViolation(
                    rule_name=f"Incompatibilidad: {a_name} → {b_name}",
                    category=RuleCategory.INCOMPATIBILITY.value,
                    detail=f"No se permite asignar '{b_name}' después de '{a_name}' "
                           f"(día adyacente: {adj.date})",
                ))

    return violations


async def validate_assignment_rules(
    db: AsyncSession, employee_id: UUID, shift_type_id: UUID,
    target_date: date, exclude_id: UUID | None = None,
) -> tuple[List[RuleViolation], List[RuleViolation]]:
    """
    Ejecuta todas las validaciones de reglas de negocio.
    Retorna (errores, advertencias).
    """
    # Obtener datos del empleado
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()
    emp_cat_id = employee.category_id if employee else None

    # Obtener shift type
    st_result = await db.execute(select(ShiftType).where(ShiftType.id == shift_type_id))
    shift_type = st_result.scalar_one_or_none()

    errors: List[RuleViolation] = []
    warnings: List[RuleViolation] = []

    if not shift_type:
        return errors, warnings

    # Ejecutar todas las validaciones
    errors.extend(await validate_max_weekly_hours(
        db, employee_id, target_date, shift_type, emp_cat_id, exclude_id
    ))
    errors.extend(await validate_consecutive_days(
        db, employee_id, target_date, emp_cat_id, exclude_id
    ))
    errors.extend(await validate_weekly_rest(
        db, employee_id, target_date, emp_cat_id, exclude_id
    ))
    errors.extend(await validate_shift_incompatibilities(
        db, employee_id, target_date, shift_type_id, exclude_id
    ))

    return errors, warnings
