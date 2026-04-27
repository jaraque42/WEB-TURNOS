from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_token, verify_password
from app.models.user import User
from app.models.role import Role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    username: str = payload.get("sub")
    if not username:
        raise credentials_exception

    result = await db.execute(
        select(User)
        .options(selectinload(User.role).selectinload(Role.permissions))
        .where(User.username == username)
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise credentials_exception

    # Actualizar último login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    return user


async def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos suficientes",
        )
    return current_user


def require_permission(*required_permissions: str):
    """Dependency factory que verifica que el usuario tenga los permisos indicados.

    Uso:
        @router.get("/", dependencies=[Depends(require_permission("users:read"))])

    Los superusuarios siempre pasan la validación.
    """

    async def _check(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        # Reutiliza get_current_user para obtener el usuario autenticado
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
        payload = decode_token(token)
        if not payload:
            raise credentials_exception

        username: str = payload.get("sub")
        if not username:
            raise credentials_exception

        result = await db.execute(
            select(User)
            .options(
                selectinload(User.role).selectinload(Role.permissions)
            )
            .where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise credentials_exception

        # Superusuarios siempre tienen acceso
        if user.is_superuser:
            return user

        # Verificar permisos del rol
        if not user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes un rol asignado",
            )

        user_perms = {p.name for p in user.role.permissions}
        missing = set(required_permissions) - user_perms
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Faltan: {', '.join(sorted(missing))}",
            )

        return user

    return _check
