from typing import List
from uuid import UUID
import csv
import io
import re
import unicodedata

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserCreate, UserOut, UserUpdate, ChangePassword, UserBulkResult
from app.services.auth import get_current_superuser, get_current_user
from app.services import user as user_service

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.post("/me/change-password")
async def change_my_password(
    body: ChangePassword,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cambiar la contraseña del usuario autenticado."""
    await user_service.change_own_password(
        db, current_user, body.current_password, body.new_password
    )
    return {"detail": "Contraseña actualizada"}


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """Admin resetea la contraseña de cualquier usuario."""
    new_password = body.get("new_password")
    if not new_password:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=400, detail="new_password es requerido")
    await user_service.reset_user_password(db, user_id, new_password)
    return {"detail": "Contraseña reseteada"}


@router.get("/", response_model=List[UserOut])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await user_service.get_users(db, skip=skip, limit=limit)


@router.post("/", response_model=UserOut, status_code=201)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    return await user_service.create_user(db, user_in)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await user_service.get_user_by_id(db, user_id)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    return await user_service.update_user(db, user_id, user_in)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    await user_service.delete_user(db, user_id)


@router.post("/bulk/", response_model=UserBulkResult, status_code=201)
async def bulk_create_users(
    users_data: List[UserCreate],
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """Crear múltiples usuarios de una vez."""
    created_users, errors = await user_service.bulk_create_users(db, users_data)
    
    return UserBulkResult(
        created=len(created_users),
        failed=len(errors),
        errors=errors,
    )


_ALIAS_MAP = {
    "username": {"username", "usuario", "user", "login", "id_usuario"},
    "email": {"email", "correo", "mail", "e_mail", "user_email"},
    "full_name": {"full_name", "nombre", "nombre_completo", "nombrecompleto", "name", "display_name"},
    "password": {"password", "contrasena", "clave", "pass", "pwd"},
    "role_name": {"role_name", "rol", "tipo_usuario", "perfil", "role", "user_role"},
    "is_superuser": {"is_superuser", "superusuario", "admin", "es_admin", "es_superuser", "superuser"},
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

@router.post("/upload-csv/", response_model=UserBulkResult, status_code=201)
async def upload_users_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("users:create")),
):
    """
    Subir un CSV/XLSX con usuarios. Soporta cabeceras flexibles (español/inglés).
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
                    if isinstance(val, (datetime.datetime, datetime.date)):
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
    
    # Obtener mapeo de roles por nombre
    result = await db.execute(select(Role))
    roles = {role.name: role.id for role in result.scalars().all()}

    users_to_create = []
    parse_errors = []

    for idx, raw_row in enumerate(csv_reader, start=2):  # start=2 porque la fila 1 es el encabezado
        row = _normalize_row(raw_row)
        try:
            # Validar campos requeridos
            required_fields = ['username', 'email', 'full_name', 'password']
            missing = [f for f in required_fields if not row.get(f)]
            if missing:
                parse_errors.append(f"Fila {idx}: Faltan campos: {', '.join(missing)}")
                continue

            # Obtener role_id si se especificó role_name
            role_id = None
            role_name = row.get('role_name', '').strip()
            if role_name:
                role_id = roles.get(role_name)
                if not role_id:
                    parse_errors.append(f"Fila {idx}: Rol '{role_name}' no encontrado")
                    continue

            # Parsear is_superuser
            is_superuser_str = row.get('is_superuser', 'false').strip().lower()
            is_superuser = is_superuser_str in ('true', '1', 'yes', 'sí', 'si')

            users_to_create.append(UserCreate(
                username=row['username'].strip(),
                email=row['email'].strip(),
                full_name=row['full_name'].strip(),
                password=row['password'].strip(),
                role_id=role_id,
                is_superuser=is_superuser,
            ))

        except Exception as e:
            parse_errors.append(f"Fila {idx}: Error al parsear: {str(e)}")
            continue

    # Crear usuarios
    created_users, creation_errors = await user_service.bulk_create_users(db, users_to_create)
    
    all_errors = parse_errors + creation_errors

    return UserBulkResult(
        created=len(created_users),
        failed=len(parse_errors) + len(creation_errors),
        errors=all_errors,
    )
