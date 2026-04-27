from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.role import PermissionCreate, PermissionOut, PermissionUpdate
from app.services.auth import get_current_superuser, get_current_user
from app.services import permission as permission_service

router = APIRouter(prefix="/permissions", tags=["Permisos"])


@router.get("/", response_model=List[PermissionOut])
async def list_permissions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Listar todos los permisos."""
    return await permission_service.get_permissions(db, skip, limit)


@router.post("/", response_model=PermissionOut, status_code=201)
async def create_permission(
    perm_in: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """Crear un nuevo permiso (solo superusuarios)."""
    return await permission_service.create_permission(db, perm_in)


@router.get("/{permission_id}", response_model=PermissionOut)
async def get_permission(
    permission_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Obtener un permiso por ID."""
    return await permission_service.get_permission_by_id(db, permission_id)


@router.patch("/{permission_id}", response_model=PermissionOut)
async def update_permission(
    permission_id: UUID,
    perm_in: PermissionUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """Actualizar un permiso (solo superusuarios)."""
    return await permission_service.update_permission(db, permission_id, perm_in)


@router.delete("/{permission_id}", status_code=204)
async def delete_permission(
    permission_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """Eliminar un permiso (solo superusuarios). Falla si está asignado a roles."""
    await permission_service.delete_permission(db, permission_id)
