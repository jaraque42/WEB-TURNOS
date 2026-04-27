from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.role import Role, Permission
from app.models.user import User
from app.schemas.role import RoleCreate, RoleOut, RoleUpdate
from app.services.auth import get_current_superuser, get_current_user

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=List[RoleOut])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Role).options(selectinload(Role.permissions)))
    return result.scalars().all()


@router.post("/", response_model=RoleOut, status_code=201)
async def create_role(
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    role = Role(name=role_in.name, description=role_in.description)

    if role_in.permission_ids:
        result = await db.execute(
            select(Permission).where(Permission.id.in_(role_in.permission_ids))
        )
        role.permissions = result.scalars().all()

    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


@router.patch("/{role_id}", response_model=RoleOut)
async def update_role(
    role_id: UUID,
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    if role_in.name is not None:
        role.name = role_in.name
    if role_in.description is not None:
        role.description = role_in.description
    if role_in.is_active is not None:
        role.is_active = role_in.is_active
    if role_in.permission_ids is not None:
        perm_result = await db.execute(
            select(Permission).where(Permission.id.in_(role_in.permission_ids))
        )
        role.permissions = perm_result.scalars().all()

    await db.commit()
    await db.refresh(role)
    return role


@router.delete("/{role_id}", status_code=204)
async def delete_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    result = await db.execute(
        select(Role).options(selectinload(Role.users)).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    if role.users:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede eliminar: el rol '{role.name}' tiene {len(role.users)} usuario(s) asignado(s)",
        )

    await db.delete(role)
    await db.commit()
