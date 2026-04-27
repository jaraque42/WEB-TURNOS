from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Permission
from app.schemas.role import PermissionCreate, PermissionUpdate


async def get_permissions(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Permission]:
    result = await db.execute(
        select(Permission).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def get_permission_by_id(db: AsyncSession, permission_id: UUID) -> Optional[Permission]:
    result = await db.execute(
        select(Permission).where(Permission.id == permission_id)
    )
    permission = result.scalar_one_or_none()
    if not permission:
        raise HTTPException(status_code=404, detail="Permiso no encontrado")
    return permission


async def create_permission(db: AsyncSession, perm_in: PermissionCreate) -> Permission:
    # Verificar duplicado
    result = await db.execute(
        select(Permission).where(Permission.name == perm_in.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un permiso con el nombre '{perm_in.name}'",
        )

    permission = Permission(name=perm_in.name, description=perm_in.description)
    db.add(permission)
    await db.commit()
    await db.refresh(permission)
    return permission


async def update_permission(
    db: AsyncSession, permission_id: UUID, perm_in: PermissionUpdate
) -> Permission:
    permission = await get_permission_by_id(db, permission_id)

    if perm_in.name is not None:
        # Verificar que no exista otro permiso con ese nombre
        result = await db.execute(
            select(Permission).where(
                Permission.name == perm_in.name, Permission.id != permission_id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un permiso con el nombre '{perm_in.name}'",
            )
        permission.name = perm_in.name

    if perm_in.description is not None:
        permission.description = perm_in.description

    await db.commit()
    await db.refresh(permission)
    return permission


async def delete_permission(db: AsyncSession, permission_id: UUID) -> None:
    permission = await get_permission_by_id(db, permission_id)

    # Verificar que no esté asignado a ningún rol
    result = await db.execute(
        select(Permission)
        .options(selectinload(Permission.roles))
        .where(Permission.id == permission_id)
    )
    perm_with_roles = result.scalar_one()
    if perm_with_roles.roles:
        role_names = ", ".join(r.name for r in perm_with_roles.roles)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede eliminar: el permiso está asignado a los roles: {role_names}",
        )

    await db.delete(permission)
    await db.commit()
