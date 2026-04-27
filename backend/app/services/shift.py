from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.shift import ShiftType, CoverageRequirement
from app.models.assignment import ShiftAssignment
from app.schemas.shift import (
    ShiftTypeCreate, ShiftTypeUpdate,
    CoverageRequirementCreate, CoverageRequirementUpdate,
    CoverageBulkCreate,
)


# ─── Tipo de Turno ──────────────────────────────────────

async def get_shift_types(db: AsyncSession, skip: int = 0, limit: int = 100, active_only: bool = False) -> List[ShiftType]:
    query = select(ShiftType)
    if active_only:
        query = query.where(ShiftType.is_active == True)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


async def get_shift_type_by_id(db: AsyncSession, shift_type_id: UUID) -> ShiftType:
    result = await db.execute(select(ShiftType).where(ShiftType.id == shift_type_id))
    st = result.scalar_one_or_none()
    if not st:
        raise HTTPException(status_code=404, detail="Tipo de turno no encontrado")
    return st


async def create_shift_type(db: AsyncSession, data: ShiftTypeCreate) -> ShiftType:
    # Verificar nombre duplicado
    result = await db.execute(select(ShiftType).where(ShiftType.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Ya existe el tipo de turno '{data.name}'")

    # Verificar código duplicado
    result = await db.execute(select(ShiftType).where(ShiftType.code == data.code))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Ya existe un tipo de turno con código '{data.code}'")

    st = ShiftType(
        name=data.name,
        code=data.code,
        description=data.description,
        start_time=data.start_time,
        end_time=data.end_time,
        duration_hours=data.duration_hours,
        color=data.color,
    )
    db.add(st)
    await db.commit()
    await db.refresh(st)
    return st


async def update_shift_type(db: AsyncSession, shift_type_id: UUID, data: ShiftTypeUpdate) -> ShiftType:
    st = await get_shift_type_by_id(db, shift_type_id)
    update_data = data.model_dump(exclude_unset=True)

    if "name" in update_data:
        result = await db.execute(
            select(ShiftType).where(ShiftType.name == update_data["name"], ShiftType.id != shift_type_id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Ya existe el tipo de turno '{update_data['name']}'")

    if "code" in update_data:
        result = await db.execute(
            select(ShiftType).where(ShiftType.code == update_data["code"], ShiftType.id != shift_type_id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Ya existe un tipo de turno con código '{update_data['code']}'")

    for field, value in update_data.items():
        setattr(st, field, value)

    await db.commit()
    await db.refresh(st)
    return st


async def delete_shift_type(db: AsyncSession, shift_type_id: UUID) -> None:
    st = await get_shift_type_by_id(db, shift_type_id)

    # Eliminar en cascada todas las coberturas asociadas
    await db.execute(
        delete(CoverageRequirement).where(CoverageRequirement.shift_type_id == shift_type_id)
    )

    # Eliminar en cascada todas las asignaciones asociadas
    await db.execute(
        delete(ShiftAssignment).where(ShiftAssignment.shift_type_id == shift_type_id)
    )

    # Ahora eliminar el tipo de turno
    await db.delete(st)
    await db.commit()


# ─── Cobertura ──────────────────────────────────────────

async def get_coverage_requirements(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    shift_type_id: Optional[UUID] = None,
    location: Optional[str] = None,
) -> List[CoverageRequirement]:
    query = select(CoverageRequirement).options(selectinload(CoverageRequirement.shift_type))

    if start_date:
        query = query.where(CoverageRequirement.date >= start_date)
    if end_date:
        query = query.where(CoverageRequirement.date <= end_date)
    if shift_type_id:
        query = query.where(CoverageRequirement.shift_type_id == shift_type_id)
    if location:
        query = query.where(CoverageRequirement.location == location)

    query = query.order_by(CoverageRequirement.date).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_coverage_by_id(db: AsyncSession, coverage_id: UUID) -> CoverageRequirement:
    result = await db.execute(
        select(CoverageRequirement)
        .options(selectinload(CoverageRequirement.shift_type))
        .where(CoverageRequirement.id == coverage_id)
    )
    cov = result.scalar_one_or_none()
    if not cov:
        raise HTTPException(status_code=404, detail="Requerimiento de cobertura no encontrado")
    return cov


async def create_coverage(db: AsyncSession, data: CoverageRequirementCreate) -> CoverageRequirement:
    # Verificar que el tipo de turno existe
    await get_shift_type_by_id(db, data.shift_type_id)

    # Validar max >= min
    if data.max_employees is not None and data.max_employees < data.min_employees:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="max_employees no puede ser menor que min_employees",
        )

    cov = CoverageRequirement(
        date=data.date,
        min_employees=data.min_employees,
        max_employees=data.max_employees,
        location=data.location,
        shift_type_id=data.shift_type_id,
    )
    db.add(cov)
    await db.commit()

    return await get_coverage_by_id(db, cov.id)


async def update_coverage(db: AsyncSession, coverage_id: UUID, data: CoverageRequirementUpdate) -> CoverageRequirement:
    cov = await get_coverage_by_id(db, coverage_id)
    update_data = data.model_dump(exclude_unset=True)

    if "shift_type_id" in update_data:
        await get_shift_type_by_id(db, update_data["shift_type_id"])

    for field, value in update_data.items():
        setattr(cov, field, value)

    # Validar max >= min después de aplicar cambios
    if cov.max_employees is not None and cov.max_employees < cov.min_employees:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="max_employees no puede ser menor que min_employees",
        )

    await db.commit()
    return await get_coverage_by_id(db, coverage_id)


async def delete_coverage(db: AsyncSession, coverage_id: UUID) -> None:
    cov = await get_coverage_by_id(db, coverage_id)
    await db.delete(cov)
    await db.commit()


async def bulk_create_coverage(db: AsyncSession, data: CoverageBulkCreate) -> List[CoverageRequirement]:
    """Crear coberturas para un rango de fechas y múltiples tipos de turno."""
    if data.end_date < data.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date no puede ser anterior a start_date",
        )

    if data.max_employees is not None and data.max_employees < data.min_employees:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="max_employees no puede ser menor que min_employees",
        )

    # Verificar que todos los tipos de turno existen
    for st_id in data.shift_type_ids:
        await get_shift_type_by_id(db, st_id)

    created = []
    current = data.start_date
    while current <= data.end_date:
        for st_id in data.shift_type_ids:
            # Verificar si ya existe para evitar duplicados
            result = await db.execute(
                select(CoverageRequirement).where(
                    and_(
                        CoverageRequirement.date == current,
                        CoverageRequirement.shift_type_id == st_id,
                        CoverageRequirement.location == data.location,
                    )
                )
            )
            if result.scalar_one_or_none():
                continue  # ya existe, la saltea

            cov = CoverageRequirement(
                date=current,
                min_employees=data.min_employees,
                max_employees=data.max_employees,
                location=data.location,
                shift_type_id=st_id,
            )
            db.add(cov)
            created.append(cov)

        current += timedelta(days=1)

    await db.commit()

    # Refrescar con relaciones
    result_list = []
    for c in created:
        result_list.append(await get_coverage_by_id(db, c.id))

    return result_list
