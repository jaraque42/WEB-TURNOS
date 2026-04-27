from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, and_, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assignment import ShiftAssignment, AssignmentStatus, SwapRequest, SwapRequestStatus
from app.models.employee import Employee, EmployeeStatus, License, LicenseStatus
from app.models.shift import ShiftType
from app.schemas.assignment import (
    ShiftAssignmentCreate, ShiftAssignmentUpdate,
    BulkAssignmentCreate, BulkAssignmentResult,
    SwapRequestCreate, SwapRequestUpdate,
    AssignmentStats,
)
from app.services.business_rule import validate_assignment_rules


# ═══════════════════════════════════════════════════════════
#  Validaciones de Negocio
# ═══════════════════════════════════════════════════════════

async def _validate_employee_exists(db: AsyncSession, employee_id: UUID) -> Employee:
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    if emp.status != EmployeeStatus.ACTIVE:
        raise HTTPException(
            status_code=409,
            detail=f"El empleado no está activo (estado: {emp.status.value})"
        )
    return emp


async def _validate_shift_type_exists(db: AsyncSession, shift_type_id: UUID) -> ShiftType:
    result = await db.execute(select(ShiftType).where(ShiftType.id == shift_type_id))
    st = result.scalar_one_or_none()
    if not st:
        raise HTTPException(status_code=404, detail="Tipo de turno no encontrado")
    if not st.is_active:
        raise HTTPException(status_code=409, detail="El tipo de turno está desactivado")
    return st


async def _check_employee_on_leave(db: AsyncSession, employee_id: UUID, target_date: date) -> None:
    """Verifica que el empleado no tenga licencia aprobada en esa fecha."""
    result = await db.execute(
        select(License).where(
            and_(
                License.employee_id == employee_id,
                License.status == LicenseStatus.APPROVED,
                License.start_date <= target_date,
                License.end_date >= target_date,
            )
        )
    )
    lic = result.scalar_one_or_none()
    if lic:
        raise HTTPException(
            status_code=409,
            detail=f"El empleado tiene licencia aprobada ({lic.license_type.value}) "
                   f"del {lic.start_date} al {lic.end_date}",
        )


async def _check_duplicate_assignment(
    db: AsyncSession, employee_id: UUID, target_date: date, exclude_id: UUID | None = None
) -> None:
    """Verifica que el empleado no tenga ya una asignación activa en esa fecha."""
    query = select(ShiftAssignment).where(
        and_(
            ShiftAssignment.employee_id == employee_id,
            ShiftAssignment.date == target_date,
            ShiftAssignment.status != AssignmentStatus.CANCELLED,
        )
    )
    if exclude_id:
        query = query.where(ShiftAssignment.id != exclude_id)
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"El empleado ya tiene una asignación para el {target_date}",
        )


async def _check_rest_period(
    db: AsyncSession, employee_id: UUID, target_date: date,
    shift_type: ShiftType, exclude_id: UUID | None = None,
    min_rest_hours: int = 12,
) -> None:
    """Verifica que haya descanso mínimo entre turnos consecutivos."""
    day_before = target_date - timedelta(days=1)
    day_after = target_date + timedelta(days=1)

    # Buscar asignaciones adyacentes
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
        adj_st = adj.shift_type
        if adj.date == day_before:
            # Turno del día anterior: su fin → nuestro inicio
            from datetime import datetime as dt
            prev_end = dt.combine(day_before, adj_st.end_time)
            curr_start = dt.combine(target_date, shift_type.start_time)
            # Si end_time < start_time, el turno cruza medianoche
            if adj_st.end_time < adj_st.start_time:
                prev_end = dt.combine(target_date, adj_st.end_time)
            gap = (curr_start - prev_end).total_seconds() / 3600
        else:
            # Turno del día siguiente: nuestro fin → su inicio
            from datetime import datetime as dt
            curr_end = dt.combine(target_date, shift_type.end_time)
            if shift_type.end_time < shift_type.start_time:
                curr_end = dt.combine(day_after, shift_type.end_time)
            next_start = dt.combine(day_after, adj_st.start_time)
            gap = (next_start - curr_end).total_seconds() / 3600

        if gap < min_rest_hours:
            raise HTTPException(
                status_code=409,
                detail=f"Descanso insuficiente ({gap:.1f}h) entre turnos. "
                       f"Mínimo requerido: {min_rest_hours}h",
            )


# ═══════════════════════════════════════════════════════════
#  CRUD de Asignaciones
# ═══════════════════════════════════════════════════════════

async def get_assignments(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    date_from: date | None = None,
    date_to: date | None = None,
    employee_id: UUID | None = None,
    shift_type_id: UUID | None = None,
    assignment_status: AssignmentStatus | None = None,
    location: str | None = None,
) -> List[ShiftAssignment]:
    query = (
        select(ShiftAssignment)
        .options(selectinload(ShiftAssignment.employee), selectinload(ShiftAssignment.shift_type))
    )
    if date_from:
        query = query.where(ShiftAssignment.date >= date_from)
    if date_to:
        query = query.where(ShiftAssignment.date <= date_to)
    if employee_id:
        query = query.where(ShiftAssignment.employee_id == employee_id)
    if shift_type_id:
        query = query.where(ShiftAssignment.shift_type_id == shift_type_id)
    if assignment_status:
        query = query.where(ShiftAssignment.status == assignment_status)
    if location:
        query = query.where(ShiftAssignment.location.ilike(f"%{location}%"))

    query = query.order_by(ShiftAssignment.date, ShiftAssignment.employee_id)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


async def get_assignment_by_id(db: AsyncSession, assignment_id: UUID) -> ShiftAssignment:
    result = await db.execute(
        select(ShiftAssignment)
        .options(selectinload(ShiftAssignment.employee), selectinload(ShiftAssignment.shift_type))
        .where(ShiftAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    return assignment


async def create_assignment(db: AsyncSession, data: ShiftAssignmentCreate) -> ShiftAssignment:
    # Validaciones básicas
    await _validate_employee_exists(db, data.employee_id)
    shift_type = await _validate_shift_type_exists(db, data.shift_type_id)
    await _check_employee_on_leave(db, data.employee_id, data.date)
    await _check_duplicate_assignment(db, data.employee_id, data.date)
    await _check_rest_period(db, data.employee_id, data.date, shift_type)

    # Validaciones de reglas de negocio configurables
    errors, _ = await validate_assignment_rules(
        db, data.employee_id, data.shift_type_id, data.date
    )
    if errors:
        details = "; ".join(v.detail for v in errors)
        raise HTTPException(status_code=409, detail=f"Reglas de negocio violadas: {details}")

    assignment = ShiftAssignment(
        date=data.date,
        employee_id=data.employee_id,
        shift_type_id=data.shift_type_id,
        notes=data.notes,
        location=data.location,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment, attribute_names=["employee", "shift_type"])
    return assignment


async def update_assignment(
    db: AsyncSession, assignment_id: UUID, data: ShiftAssignmentUpdate
) -> ShiftAssignment:
    assignment = await get_assignment_by_id(db, assignment_id)

    # Si se cancela, no verificar reglas adicionales
    if data.status == AssignmentStatus.CANCELLED:
        assignment.status = AssignmentStatus.CANCELLED
        if data.notes is not None:
            assignment.notes = data.notes
        await db.commit()
        await db.refresh(assignment, attribute_names=["employee", "shift_type"])
        return assignment

    new_employee_id = data.employee_id or assignment.employee_id
    new_date = data.date or assignment.date
    new_shift_type_id = data.shift_type_id or assignment.shift_type_id

    # Si cambian empleado o fecha, revalidar
    if data.employee_id or data.date:
        await _validate_employee_exists(db, new_employee_id)
        await _check_employee_on_leave(db, new_employee_id, new_date)
        await _check_duplicate_assignment(db, new_employee_id, new_date, exclude_id=assignment_id)

    if data.employee_id or data.date or data.shift_type_id:
        shift_type = await _validate_shift_type_exists(db, new_shift_type_id)
        await _check_rest_period(db, new_employee_id, new_date, shift_type, exclude_id=assignment_id)

        # Validaciones de reglas de negocio configurables
        errors, _ = await validate_assignment_rules(
            db, new_employee_id, new_shift_type_id, new_date, exclude_id=assignment_id
        )
        if errors:
            details = "; ".join(v.detail for v in errors)
            raise HTTPException(status_code=409, detail=f"Reglas de negocio violadas: {details}")

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(assignment, field, value)

    await db.commit()
    await db.refresh(assignment, attribute_names=["employee", "shift_type"])
    return assignment


async def delete_assignment(db: AsyncSession, assignment_id: UUID) -> None:
    assignment = await get_assignment_by_id(db, assignment_id)
    # No eliminar si está completada
    if assignment.status == AssignmentStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar una asignación completada. Cancélela en su lugar.",
        )
    await db.delete(assignment)
    await db.commit()


async def bulk_delete_assignments(
    db: AsyncSession, assignment_ids: List[UUID]
) -> dict:
    """Eliminar múltiples asignaciones. Omite las completadas."""
    deleted = 0
    skipped = 0
    details: list[str] = []

    for aid in assignment_ids:
        result = await db.execute(
            select(ShiftAssignment)
            .options(selectinload(ShiftAssignment.employee), selectinload(ShiftAssignment.shift_type))
            .where(ShiftAssignment.id == aid)
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            skipped += 1
            details.append(f"ID {aid}: no encontrada")
            continue
        if assignment.status == AssignmentStatus.COMPLETED:
            skipped += 1
            emp_name = f"{assignment.employee.last_name}, {assignment.employee.first_name}" if assignment.employee else str(aid)
            details.append(f"{emp_name} ({assignment.date}): completada, no se puede eliminar")
            continue
        await db.delete(assignment)
        deleted += 1

    await db.commit()
    return {"deleted": deleted, "skipped": skipped, "details": details}


# ═══════════════════════════════════════════════════════════
#  Generación Masiva
# ═══════════════════════════════════════════════════════════

async def bulk_create_assignments(
    db: AsyncSession, data: BulkAssignmentCreate
) -> BulkAssignmentResult:
    if data.start_date > data.end_date:
        raise HTTPException(status_code=422, detail="start_date debe ser <= end_date")

    shift_type = await _validate_shift_type_exists(db, data.shift_type_id)

    created = 0
    skipped = 0
    details: list[str] = []

    current = data.start_date
    while current <= data.end_date:
        for emp_id in data.employee_ids:
            try:
                await _validate_employee_exists(db, emp_id)
                await _check_employee_on_leave(db, emp_id, current)
                await _check_duplicate_assignment(db, emp_id, current)
                await _check_rest_period(db, emp_id, current, shift_type)

                # Reglas de negocio configurables
                rule_errors, _ = await validate_assignment_rules(
                    db, emp_id, data.shift_type_id, current
                )
                if rule_errors:
                    raise HTTPException(
                        status_code=409,
                        detail="; ".join(v.detail for v in rule_errors),
                    )

                assignment = ShiftAssignment(
                    date=current,
                    employee_id=emp_id,
                    shift_type_id=data.shift_type_id,
                    location=data.location,
                )
                db.add(assignment)
                created += 1
            except HTTPException as e:
                skipped += 1
                details.append(f"{current} / empleado {emp_id}: {e.detail}")

        current += timedelta(days=1)

    await db.commit()
    return BulkAssignmentResult(created=created, skipped=skipped, details=details)


# ═══════════════════════════════════════════════════════════
#  Permutas
# ═══════════════════════════════════════════════════════════

async def create_swap_request(db: AsyncSession, data: SwapRequestCreate) -> SwapRequest:
    # Validar que ambas asignaciones existen y están activas
    req_assignment = await get_assignment_by_id(db, data.requester_assignment_id)
    tgt_assignment = await get_assignment_by_id(db, data.target_assignment_id)

    if req_assignment.status == AssignmentStatus.CANCELLED:
        raise HTTPException(status_code=409, detail="La asignación del solicitante está cancelada")
    if tgt_assignment.status == AssignmentStatus.CANCELLED:
        raise HTTPException(status_code=409, detail="La asignación objetivo está cancelada")
    if req_assignment.employee_id == tgt_assignment.employee_id:
        raise HTTPException(status_code=409, detail="No se puede permutar con uno mismo")

    swap = SwapRequest(
        requester_assignment_id=data.requester_assignment_id,
        target_assignment_id=data.target_assignment_id,
        reason=data.reason,
    )
    db.add(swap)
    await db.commit()
    await db.refresh(swap)
    return swap


async def get_swap_requests(
    db: AsyncSession, skip: int = 0, limit: int = 50,
    swap_status: SwapRequestStatus | None = None,
) -> List[SwapRequest]:
    query = select(SwapRequest).options(
        selectinload(SwapRequest.requester_assignment),
        selectinload(SwapRequest.target_assignment),
    )
    if swap_status:
        query = query.where(SwapRequest.status == swap_status)
    query = query.order_by(SwapRequest.created_at.desc())
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


async def resolve_swap_request(
    db: AsyncSession, swap_id: UUID, data: SwapRequestUpdate
) -> SwapRequest:
    result = await db.execute(select(SwapRequest).where(SwapRequest.id == swap_id))
    swap = result.scalar_one_or_none()
    if not swap:
        raise HTTPException(status_code=404, detail="Solicitud de permuta no encontrada")
    if swap.status != SwapRequestStatus.PENDING:
        raise HTTPException(status_code=409, detail="La solicitud ya fue resuelta")

    if data.status == SwapRequestStatus.APPROVED:
        # Ejecutar la permuta: intercambiar employee_id de ambas asignaciones
        req_a = await get_assignment_by_id(db, swap.requester_assignment_id)
        tgt_a = await get_assignment_by_id(db, swap.target_assignment_id)

        req_a.employee_id, tgt_a.employee_id = tgt_a.employee_id, req_a.employee_id

    swap.status = data.status
    if data.reason is not None:
        swap.reason = data.reason
    swap.resolved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(swap)
    return swap


# ═══════════════════════════════════════════════════════════
#  Estadísticas
# ═══════════════════════════════════════════════════════════

async def get_assignment_stats(
    db: AsyncSession,
    date_from: date,
    date_to: date,
) -> AssignmentStats:
    base_filter = and_(
        ShiftAssignment.date >= date_from,
        ShiftAssignment.date <= date_to,
    )

    # Total
    total_q = await db.execute(
        select(func.count(ShiftAssignment.id)).where(base_filter)
    )
    total = total_q.scalar() or 0

    # Por estado
    status_q = await db.execute(
        select(ShiftAssignment.status, func.count(ShiftAssignment.id))
        .where(base_filter)
        .group_by(ShiftAssignment.status)
    )
    by_status = {row[0].value: row[1] for row in status_q.all()}

    # Por tipo de turno
    type_q = await db.execute(
        select(ShiftType.name, func.count(ShiftAssignment.id))
        .join(ShiftType, ShiftAssignment.shift_type_id == ShiftType.id)
        .where(base_filter)
        .group_by(ShiftType.name)
    )
    by_shift_type = {row[0]: row[1] for row in type_q.all()}

    # Empleados distintos
    emp_q = await db.execute(
        select(func.count(func.distinct(ShiftAssignment.employee_id))).where(base_filter)
    )
    employees_assigned = emp_q.scalar() or 0

    return AssignmentStats(
        total_assignments=total,
        by_status=by_status,
        by_shift_type=by_shift_type,
        employees_assigned=employees_assigned,
    )
