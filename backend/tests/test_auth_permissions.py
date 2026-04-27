import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Permission, Role
from app.models.user import User
from app.core.security import get_password_hash


@pytest.mark.asyncio
class TestRequirePermission:
    """Tests para la dependency require_permission."""

    async def test_superuser_bypasses_permissions(self, client: AsyncClient, admin_token: str):
        """Un superusuario siempre tiene acceso, sin importar los permisos."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # Puede acceder a endpoints protegidos con get_current_superuser
        response = await client.get("/api/v1/users/", headers=headers)
        assert response.status_code == 200

    async def test_unauthenticated_user_rejected(self, client: AsyncClient):
        """Un usuario sin token es rechazado."""
        response = await client.get("/api/v1/permissions/")
        assert response.status_code == 401

    async def test_user_with_correct_permission_allowed(
        self, client: AsyncClient, db: AsyncSession
    ):
        """Un usuario con el permiso correcto puede acceder."""
        # Crear permiso
        perm = Permission(name="users:read", description="Leer usuarios")
        db.add(perm)
        await db.commit()
        await db.refresh(perm)

        # Crear rol con ese permiso
        role = Role(name="with_perm_role", description="Role with perm", permissions=[perm])
        db.add(role)
        await db.commit()
        await db.refresh(role)

        # Crear usuario con ese rol
        user = User(
            username="permuser",
            email="permuser@test.com",
            full_name="Perm User",
            hashed_password=get_password_hash("testpass123"),
            is_superuser=False,
            role_id=role.id,
        )
        db.add(user)
        await db.commit()

        # Login
        login_resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "permuser", "password": "testpass123"},
        )
        token = login_resp.json()["access_token"]

        # Acceso a listar permisos (requiere autenticación)
        response = await client.get(
            "/api/v1/permissions/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
