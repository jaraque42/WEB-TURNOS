from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserCreate, UserUpdate


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    result = await db.execute(
        select(User)
        .options(selectinload(User.role).selectinload(Role.permissions))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    result = await db.execute(
        select(User)
        .options(selectinload(User.role).selectinload(Role.permissions))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    # Verificar duplicados
    result = await db.execute(
        select(User).where(
            (User.username == user_in.username) | (User.email == user_in.email)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El username o email ya existe",
        )

    user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        role_id=user_in.role_id,
        is_superuser=user_in.is_superuser,
    )
    db.add(user)
    await db.commit()

    # Recargar con relaciones (role -> permissions)
    return await get_user_by_id(db, user.id)


async def update_user(db: AsyncSession, user_id: UUID, user_in: UserUpdate) -> User:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()

    # Recargar con relaciones (role -> permissions)
    return await get_user_by_id(db, user_id)


async def delete_user(db: AsyncSession, user_id: UUID) -> None:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    await db.delete(user)
    await db.commit()


async def change_own_password(
    db: AsyncSession, user: User, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta",
        )
    user.hashed_password = get_password_hash(new_password)
    await db.commit()


async def reset_user_password(
    db: AsyncSession, user_id: UUID, new_password: str
) -> None:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )
    user.hashed_password = get_password_hash(new_password)
    await db.commit()


async def bulk_create_users(
    db: AsyncSession, users_data: List[UserCreate]
) -> tuple[List[User], List[str]]:
    """
    Crea múltiples usuarios. Retorna (usuarios_creados, errores).
    Continúa con los demás usuarios si uno falla.
    """
    created_users = []
    errors = []

    for idx, user_in in enumerate(users_data):
        try:
            # Verificar duplicados
            result = await db.execute(
                select(User).where(
                    (User.username == user_in.username) | (User.email == user_in.email)
                )
            )
            if result.scalar_one_or_none():
                errors.append(f"Fila {idx + 1}: El username '{user_in.username}' o email '{user_in.email}' ya existe")
                continue

            user = User(
                username=user_in.username,
                email=user_in.email,
                full_name=user_in.full_name,
                hashed_password=get_password_hash(user_in.password),
                role_id=user_in.role_id,
                is_superuser=user_in.is_superuser,
            )
            db.add(user)
            await db.flush()  # Flush para obtener el ID sin hacer commit completo
            
            # Recargar con relaciones
            result = await db.execute(
                select(User)
                .options(selectinload(User.role).selectinload(Role.permissions))
                .where(User.id == user.id)
            )
            created_user = result.scalar_one()
            created_users.append(created_user)

        except Exception as e:
            errors.append(f"Fila {idx + 1}: {str(e)}")
            continue

    await db.commit()
    return created_users, errors
