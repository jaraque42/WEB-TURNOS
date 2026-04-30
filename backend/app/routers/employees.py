from typing import List, Optional
from uuid import UUID
import csv
import io
from datetime import date as date_type

from fastapi import APIRouter, Depends, Query, File, UploadFile, HTTPException, status, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.employee import EmployeeCategory, AgentType
from app.schemas.employee import (
    EmployeeCreate, EmployeeOut, EmployeeDetailOut, EmployeeUpdate,
    EmployeeCategoryCreate, EmployeeCategoryOut, EmployeeCategoryUpdate,
    AgentTypeCreate, AgentTypeOut, AgentTypeUpdate,
    LicenseCreate, LicenseOut, LicenseUpdate,
    EmployeeBulkResult,
)
from app.services.auth import get_current_user, get_current_superuser, require_permission
from app.services import employee as emp_service

router = APIRouter(tags=["Empleados"])


# ═══════════════════════════════════════════════════════════
#  Categorías de Empleado
# ═══════════════════════════════════════════════════════════

@router.get("/employee-categories/", response_model=List[EmployeeCategoryOut])
async def list_categories(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await emp_service.get_categories(db, skip, limit)


@router.post("/employee-categories/", response_model=EmployeeCategoryOut, status_code=201)
async def create_category(
    data: EmployeeCategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:create")),
):
    return await emp_service.create_category(db, data)


@router.get("/employee-categories/{category_id}", response_model=EmployeeCategoryOut)
async def get_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await emp_service.get_category_by_id(db, category_id)


@router.patch("/employee-categories/{category_id}", response_model=EmployeeCategoryOut)
async def update_category(
    category_id: UUID,
    data: EmployeeCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:update")),
):
    return await emp_service.update_category(db, category_id, data)


@router.delete("/employee-categories/{category_id}", status_code=204)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:delete")),
):
    await emp_service.delete_category(db, category_id)


# ═══════════════════════════════════════════════════════════
#  Tipos de Agente
# ═══════════════════════════════════════════════════════════

@router.get("/agent-types/", response_model=List[AgentTypeOut])
async def list_agent_types(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await emp_service.get_agent_types(db, skip, limit)


@router.post("/agent-types/", response_model=AgentTypeOut, status_code=201)
async def create_agent_type(
    data: AgentTypeCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:create")),
):
    return await emp_service.create_agent_type(db, data)


@router.get("/agent-types/{agent_type_id}", response_model=AgentTypeOut)
async def get_agent_type(
    agent_type_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await emp_service.get_agent_type_by_id(db, agent_type_id)


@router.patch("/agent-types/{agent_type_id}", response_model=AgentTypeOut)
async def update_agent_type(
    agent_type_id: UUID,
    data: AgentTypeUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:update")),
):
    return await emp_service.update_agent_type(db, agent_type_id, data)


@router.delete("/agent-types/{agent_type_id}", status_code=204)
async def delete_agent_type(
    agent_type_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:delete")),
):
    await emp_service.delete_agent_type(db, agent_type_id)


# ═══════════════════════════════════════════════════════════
#  Empleados
# ═══════════════════════════════════════════════════════════

@router.get("/employees/", response_model=List[EmployeeOut])
async def list_employees(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = Query(None, description="Filtrar por estado: activo, inactivo, licencia, suspendido"),
    category_id: Optional[UUID] = Query(None),
    agent_type_id: Optional[UUID] = Query(None),
    q: Optional[str] = Query(None, description="Filtro por nombre, apellido, documento o email"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:read")),
):
    return await emp_service.get_employees(
        db, skip, limit,
        status_filter=status,
        category_id=category_id,
        agent_type_id=agent_type_id,
        name_filter=q,
    )


@router.post("/employees/", response_model=EmployeeDetailOut, status_code=201)
async def create_employee(
    data: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:create")),
):
    return await emp_service.create_employee(db, data)


@router.post("/employees/bulk/", response_model=EmployeeBulkResult, status_code=201)
async def bulk_create_employees(
    employees_data: List[EmployeeCreate],
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:create")),
):
    """Crear múltiples empleados de una vez."""
    created_employees, errors = await emp_service.bulk_create_employees(db, employees_data)
    
    return EmployeeBulkResult(
        created=len(created_employees),
        failed=len(errors),
        errors=errors,
    )


import re
import unicodedata

_ALIAS_MAP = {
    "full_name": {"full_name", "nombre", "nombre_completo", "nombrecompleto", "name", "employee_name"},
    "document_number": {"document_number", "documento", "dni", "nie", "nif", "document_number", "documentnumber", "cedula"},
    "email": {"email", "correo", "mail", "e_mail", "employee_email"},
    "phone": {"phone", "telefono", "tel", "celular", "mobile"},
    "location": {"location", "ubicacion", "site", "sede", "base", "posicion"},
    "hire_date": {"hire_date", "fecha_ingreso", "fecha_alta", "fecha", "date", "hiredate"},
    "category_name": {"category_name", "puesto", "categoria", "puesto_asignado", "category", "role"},
    "agent_type_name": {"agent_type_name", "tipo_contrato", "tipo_agente", "tipo", "agent_type", "contract_type"},
}

def _normalize_key(key: str) -> str:
    text = unicodedata.normalize("NFKD", str(key)).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower())
    return re.sub(r"_+", "_", text).strip("_")

def _canonical_key(raw_key: str) -> str:
    nk = _normalize_key(raw_key)
    for canonical, aliases in _ALIAS_MAP.items():
        if nk in aliases:
            return canonical
    return nk

def _normalize_row(row: dict) -> dict:
    normalized: dict = {}
    for k, v in row.items():
        if k is None:
            continue
        ck = _canonical_key(k)
        val = v.strip() if isinstance(v, str) else v
        if ck not in normalized or normalized[ck] in (None, ""):
            normalized[ck] = val
    return normalized

@router.post("/employees/upload-csv/", response_model=EmployeeBulkResult, status_code=201)
async def upload_employees_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:create")),
):
    """
    Subir un CSV/XLSX con empleados. Soporta cabeceras flexibles (español/inglés).
    """
    if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser CSV o XLSX"
        )

    content = await file.read()
    csv_reader = []

    if file.filename.endswith('.xlsx'):
        import openpyxl
        import datetime
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        sheet = wb.active
        
        # Obtener encabezados
        headers = [str(cell.value).strip() if cell.value else "" for cell in sheet[1]]
        
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if not any(row):
                continue
            row_dict = {}
            for col_idx, header in enumerate(headers):
                if header:
                    val = row[col_idx]
                    if isinstance(val, datetime.datetime):
                        val = val.strftime('%Y-%m-%d')
                    row_dict[header] = str(val).strip() if val is not None else ""
            csv_reader.append(row_dict)
    else:
        # Parsear CSV
        try:
            decoded_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo debe estar en formato UTF-8"
            )
        csv_reader_obj = csv.DictReader(io.StringIO(decoded_content))
        csv_reader = list(csv_reader_obj)
    
    # Obtener mapeo de categorías y tipos de agente por nombre
    result = await db.execute(select(EmployeeCategory))
    categories = {cat.name: cat.id for cat in result.scalars().all()}
    
    result = await db.execute(select(AgentType))
    agent_types = {at.name: at.id for at in result.scalars().all()}

    employees_to_create = []
    parse_errors = []

    for idx, raw_row in enumerate(csv_reader, start=2):  # start=2 porque la fila 1 es el encabezado
        row = _normalize_row(raw_row)
        try:
            # Validar campos requeridos
            required_fields = ['full_name', 'document_number', 'hire_date']
            missing = [f for f in required_fields if not row.get(f)]
            if missing:
                parse_errors.append(f"Fila {idx}: Faltan campos obligatorios. Asegúrese de que las columnas tengan nombres correctos (ej: nombre, dni, fecha)")
                continue

            # Parsear hire_date
            from app.routers.imports import _parse_date
            hire_date = _parse_date(row['hire_date'])
            if not hire_date:
                parse_errors.append(f"Fila {idx}: Fecha de contratación '{row['hire_date']}' inválida. Usa formato YYYY-MM-DD")
                continue

            # Obtener category_id si se especificó category_name
            category_id = None
            category_name = row.get('category_name', '').strip()
            if category_name:
                category_id = categories.get(category_name)
                if not category_id:
                    parse_errors.append(f"Fila {idx}: Categoría '{category_name}' no encontrada")
                    continue

            # Obtener agent_type_id si se especificó agent_type_name
            agent_type_id = None
            agent_type_name = row.get('agent_type_name', '').strip()
            if agent_type_name:
                agent_type_id = agent_types.get(agent_type_name)
                if not agent_type_id:
                    parse_errors.append(f"Fila {idx}: Tipo de agente '{agent_type_name}' no encontrado")
                    continue

            employees_to_create.append(EmployeeCreate(
                full_name=row['full_name'].strip(),
                document_number=row['document_number'].strip(),
                email=row.get('email', '').strip() or None,
                phone=row.get('phone', '').strip() or None,
                location=row.get('location', '').strip() or None,
                hire_date=hire_date,
                category_id=category_id,
                agent_type_id=agent_type_id,
            ))

        except Exception as e:
            parse_errors.append(f"Fila {idx}: Error al parsear: {str(e)}")
            continue

    # Crear empleados
    created_employees, creation_errors = await emp_service.bulk_create_employees(db, employees_to_create)
    
    all_errors = parse_errors + creation_errors

    return EmployeeBulkResult(
        created=len(created_employees),
        failed=len(parse_errors) + len(creation_errors),
        errors=all_errors,
    )


@router.get("/employees/{employee_id}", response_model=EmployeeDetailOut)
async def get_employee(
    employee_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:read")),
):
    return await emp_service.get_employee_by_id(db, employee_id)


@router.patch("/employees/{employee_id}", response_model=EmployeeDetailOut)
async def update_employee(
    employee_id: UUID,
    data: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:update")),
):
    return await emp_service.update_employee(db, employee_id, data)


@router.delete("/employees/{employee_id}", status_code=204)
async def delete_employee(
    employee_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:delete")),
):
    await emp_service.delete_employee(db, employee_id)


@router.post("/employees/bulk-delete", status_code=200)
async def bulk_delete_employees(
    ids: List[UUID] = Body(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """Elimina múltiples empleados. Solo superusuarios."""
    deleted = await emp_service.bulk_delete_employees(db, ids)
    return {"deleted": deleted}


# ═══════════════════════════════════════════════════════════
#  Licencias de Empleados
# ═══════════════════════════════════════════════════════════

@router.get("/employees/{employee_id}/licenses/", response_model=List[LicenseOut])
async def list_employee_licenses(
    employee_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:read")),
):
    return await emp_service.get_licenses_by_employee(db, employee_id)


@router.post("/licenses/", response_model=LicenseOut, status_code=201)
async def create_license(
    data: LicenseCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:update")),
):
    return await emp_service.create_license(db, data)


@router.get("/licenses/{license_id}", response_model=LicenseOut)
async def get_license(
    license_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:read")),
):
    return await emp_service.get_license_by_id(db, license_id)


@router.patch("/licenses/{license_id}", response_model=LicenseOut)
async def update_license(
    license_id: UUID,
    data: LicenseUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:update")),
):
    return await emp_service.update_license(db, license_id, data)


@router.delete("/licenses/{license_id}", status_code=204)
async def delete_license(
    license_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("employees:delete")),
):
    await emp_service.delete_license(db, license_id)
