from typing import List
from uuid import UUID
import csv
import io

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


@router.post("/upload-csv/", response_model=UserBulkResult, status_code=201)
async def upload_users_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """
    Subir un CSV con usuarios. Formato esperado:
    username,email,full_name,password,role_name,is_superuser
    jperez,jperez@example.com,Juan Pérez,Pass1234,Admin,false
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser CSV"
        )

    # Leer el contenido del archivo
    content = await file.read()
    try:
        decoded_content = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe estar en formato UTF-8"
        )

    # Parsear CSV
    csv_reader = csv.DictReader(io.StringIO(decoded_content))
    
    # Obtener mapeo de roles por nombre
    result = await db.execute(select(Role))
    roles = {role.name: role.id for role in result.scalars().all()}

    users_to_create = []
    parse_errors = []

    for idx, row in enumerate(csv_reader, start=2):  # start=2 porque la fila 1 es el encabezado
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
