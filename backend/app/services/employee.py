from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.employee import Employee, EmployeeCategory, AgentType, License
from app.schemas.employee import (
    EmployeeCreate, EmployeeUpdate,
    EmployeeCategoryCreate, EmployeeCategoryUpdate,
    AgentTypeCreate, AgentTypeUpdate,
    LicenseCreate, LicenseUpdate,
)


# ─── Categoría de Empleado ──────────────────────────────

async def get_categories(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[EmployeeCategory]:
    result = await db.execute(select(EmployeeCategory).offset(skip).limit(limit))
    return result.scalars().all()


async def get_category_by_id(db: AsyncSession, category_id: UUID) -> EmployeeCategory:
    result = await db.execute(select(EmployeeCategory).where(EmployeeCategory.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return cat


async def create_category(db: AsyncSession, data: EmployeeCategoryCreate) -> EmployeeCategory:
    result = await db.execute(select(EmployeeCategory).where(EmployeeCategory.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Ya existe la categoría '{data.name}'")
    cat = EmployeeCategory(name=data.name, description=data.description)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


async def update_category(db: AsyncSession, category_id: UUID, data: EmployeeCategoryUpdate) -> EmployeeCategory:
    cat = await get_category_by_id(db, category_id)
    if data.name is not None:
        exists = await db.execute(
            select(EmployeeCategory).where(EmployeeCategory.name == data.name, EmployeeCategory.id != category_id)
        )
        if exists.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Ya existe la categoría '{data.name}'")
        cat.name = data.name
    if data.description is not None:
        cat.description = data.description
    if data.is_active is not None:
        cat.is_active = data.is_active
    await db.commit()
    await db.refresh(cat)
    return cat


async def delete_category(db: AsyncSession, category_id: UUID) -> None:
    cat = await get_category_by_id(db, category_id)
    result = await db.execute(select(Employee).where(Employee.category_id == category_id).limit(1))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="No se puede eliminar: tiene empleados asignados")
    await db.delete(cat)
    await db.commit()


# ─── Tipo de Agente ─────────────────────────────────────

async def get_agent_types(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[AgentType]:
    result = await db.execute(select(AgentType).offset(skip).limit(limit))
    return result.scalars().all()


async def get_agent_type_by_id(db: AsyncSession, agent_type_id: UUID) -> AgentType:
    result = await db.execute(select(AgentType).where(AgentType.id == agent_type_id))
    at = result.scalar_one_or_none()
    if not at:
        raise HTTPException(status_code=404, detail="Tipo de agente no encontrado")
    return at


async def create_agent_type(db: AsyncSession, data: AgentTypeCreate) -> AgentType:
    result = await db.execute(select(AgentType).where(AgentType.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Ya existe el tipo de agente '{data.name}'")
    at = AgentType(name=data.name, description=data.description)
    db.add(at)
    await db.commit()
    await db.refresh(at)
    return at


async def update_agent_type(db: AsyncSession, agent_type_id: UUID, data: AgentTypeUpdate) -> AgentType:
    at = await get_agent_type_by_id(db, agent_type_id)
    if data.name is not None:
        exists = await db.execute(
            select(AgentType).where(AgentType.name == data.name, AgentType.id != agent_type_id)
        )
        if exists.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Ya existe el tipo de agente '{data.name}'")
        at.name = data.name
    if data.description is not None:
        at.description = data.description
    if data.is_active is not None:
        at.is_active = data.is_active
    await db.commit()
    await db.refresh(at)
    return at


async def delete_agent_type(db: AsyncSession, agent_type_id: UUID) -> None:
    at = await get_agent_type_by_id(db, agent_type_id)
    result = await db.execute(select(Employee).where(Employee.agent_type_id == agent_type_id).limit(1))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="No se puede eliminar: tiene empleados asignados")
    await db.delete(at)
    await db.commit()


# ─── Empleado ───────────────────────────────────────────

async def get_employees(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    category_id: Optional[UUID] = None,
    agent_type_id: Optional[UUID] = None,
    name_filter: Optional[str] = None,
) -> List[Employee]:
    query = select(Employee).options(
        selectinload(Employee.category),
        selectinload(Employee.agent_type),
    )
    if status_filter:
        query = query.where(Employee.status == status_filter)
    if category_id:
        query = query.where(Employee.category_id == category_id)
    if agent_type_id:
        query = query.where(Employee.agent_type_id == agent_type_id)
    if name_filter:
        term = f"%{name_filter.strip()}%"
        query = query.where(
            or_(
                Employee.full_name.ilike(term),
                Employee.document_number.ilike(term),
                Employee.email.ilike(term),
            )
        )
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_employee_by_id(db: AsyncSession, employee_id: UUID) -> Employee:
    result = await db.execute(
        select(Employee)
        .options(
            selectinload(Employee.category),
            selectinload(Employee.agent_type),
            selectinload(Employee.licenses),
        )
        .where(Employee.id == employee_id)
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return emp


async def create_employee(db: AsyncSession, data: EmployeeCreate) -> Employee:
    # Verificar documento duplicado
    result = await db.execute(
        select(Employee).where(Employee.document_number == data.document_number)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"El documento '{data.document_number}' ya existe")

    # Verificar user_id único si se proporciona
    if data.user_id:
        result = await db.execute(select(Employee).where(Employee.user_id == data.user_id))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Ese usuario ya está vinculado a otro empleado")

    emp = Employee(
        full_name=data.full_name,
        email=data.email,
        document_number=data.document_number,
        phone=data.phone,
        location=data.location,
        hire_date=data.hire_date,
        category_id=data.category_id,
        agent_type_id=data.agent_type_id,
        user_id=data.user_id,
    )
    db.add(emp)
    await db.commit()

    # Refrescar con relaciones cargadas
    return await get_employee_by_id(db, emp.id)


async def update_employee(db: AsyncSession, employee_id: UUID, data: EmployeeUpdate) -> Employee:
    emp = await get_employee_by_id(db, employee_id)

    update_data = data.model_dump(exclude_unset=True)

    # Verificar documento duplicado
    if "document_number" in update_data:
        result = await db.execute(
            select(Employee).where(
                Employee.document_number == update_data["document_number"],
                Employee.id != employee_id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Ese documento ya está registrado")

    # Verificar user_id único
    if "user_id" in update_data and update_data["user_id"]:
        result = await db.execute(
            select(Employee).where(
                Employee.user_id == update_data["user_id"],
                Employee.id != employee_id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Ese usuario ya está vinculado a otro empleado")

    for field, value in update_data.items():
        setattr(emp, field, value)

    await db.commit()
    return await get_employee_by_id(db, employee_id)


async def delete_employee(db: AsyncSession, employee_id: UUID) -> None:
    emp = await get_employee_by_id(db, employee_id)

    # impedir borrado si tiene asignaciones de turno pendientes o históricas
    # (la relación no está configurada para eliminar en cascada).
    from app.models.assignment import ShiftAssignment

    result = await db.execute(
        select(ShiftAssignment).where(ShiftAssignment.employee_id == employee_id).limit(1)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: el empleado tiene asignaciones de turno",
        )

    await db.delete(emp)
    await db.commit()


async def bulk_delete_employees(db: AsyncSession, employee_ids: List[UUID]) -> int:
    """Elimina múltiples empleados. Devuelve la cantidad eliminada."""
    if not employee_ids:
        return 0

    # comprobar si alguno tiene asignaciones antes de intentar borrarlos
    from app.models.assignment import ShiftAssignment

    result = await db.execute(
        select(ShiftAssignment.employee_id)
        .where(ShiftAssignment.employee_id.in_(employee_ids))
    )
    assigned = {row[0] for row in result.all()}
    if assigned:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No se puede eliminar: algunos empleados tienen asignaciones de turno"
                f" (ids: {', '.join(str(i) for i in assigned)})"
            ),
        )

    result = await db.execute(
        select(Employee).where(Employee.id.in_(employee_ids))
    )
    employees = result.scalars().all()
    if not employees:
        raise HTTPException(status_code=404, detail="No se encontraron empleados con los IDs proporcionados")
    for emp in employees:
        await db.delete(emp)
    await db.commit()
    return len(employees)


# ─── Licencias ──────────────────────────────────────────

async def get_licenses_by_employee(db: AsyncSession, employee_id: UUID) -> List[License]:
    # Verificar que el empleado existe
    await get_employee_by_id(db, employee_id)
    result = await db.execute(
        select(License).where(License.employee_id == employee_id).order_by(License.start_date.desc())
    )
    return result.scalars().all()


async def get_license_by_id(db: AsyncSession, license_id: UUID) -> License:
    result = await db.execute(select(License).where(License.id == license_id))
    lic = result.scalar_one_or_none()
    if not lic:
        raise HTTPException(status_code=404, detail="Licencia no encontrada")
    return lic


async def create_license(db: AsyncSession, data: LicenseCreate) -> License:
    # Verificar que el empleado existe
    await get_employee_by_id(db, data.employee_id)

    if data.end_date < data.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La fecha de fin no puede ser anterior a la de inicio",
        )

    lic = License(
        license_type=data.license_type,
        start_date=data.start_date,
        end_date=data.end_date,
        reason=data.reason,
        employee_id=data.employee_id,
    )
    db.add(lic)
    await db.commit()
    await db.refresh(lic)
    return lic


async def update_license(db: AsyncSession, license_id: UUID, data: LicenseUpdate) -> License:
    lic = await get_license_by_id(db, license_id)

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(lic, field, value)

    # Validar fechas después de aplicar cambios
    if lic.end_date < lic.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La fecha de fin no puede ser anterior a la de inicio",
        )

    await db.commit()
    await db.refresh(lic)
    return lic


async def delete_license(db: AsyncSession, license_id: UUID) -> None:
    lic = await get_license_by_id(db, license_id)
    await db.delete(lic)
    await db.commit()


# ─── Bulk Operations ────────────────────────────────────

async def bulk_create_employees(
    db: AsyncSession, employees_data: List[EmployeeCreate]
) -> tuple[List[Employee], List[str]]:
    """
    Crea múltiples empleados. Retorna (empleados_creados, errores).
    Continúa con los demás empleados si uno falla.
    """
    created_employees = []
    errors = []

    for idx, emp_in in enumerate(employees_data):
        try:
            # Verificar documento duplicado
            result = await db.execute(
                select(Employee).where(Employee.document_number == emp_in.document_number)
            )
            if result.scalar_one_or_none():
                errors.append(f"Fila {idx + 1}: El documento '{emp_in.document_number}' ya existe")
                continue

            # Verificar user_id único si se proporciona
            if emp_in.user_id:
                result = await db.execute(select(Employee).where(Employee.user_id == emp_in.user_id))
                if result.scalar_one_or_none():
                    errors.append(f"Fila {idx + 1}: El usuario ya está vinculado a otro empleado")
                    continue

            emp = Employee(
                full_name=emp_in.full_name,
                email=emp_in.email,
                document_number=emp_in.document_number,
                phone=emp_in.phone,
                hire_date=emp_in.hire_date,
                category_id=emp_in.category_id,
                agent_type_id=emp_in.agent_type_id,
                user_id=emp_in.user_id,
            )
            db.add(emp)
            await db.flush()  # Flush para obtener el ID sin hacer commit completo

            # Recargar con relaciones
            result = await db.execute(
                select(Employee)
                .options(
                    selectinload(Employee.category),
                    selectinload(Employee.agent_type),
                )
                .where(Employee.id == emp.id)
            )
            created_emp = result.scalar_one()
            created_employees.append(created_emp)

        except Exception as e:
            errors.append(f"Fila {idx + 1}: {str(e)}")
            continue

    await db.commit()
    return created_employees, errors
