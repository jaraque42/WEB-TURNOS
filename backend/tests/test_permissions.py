import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestPermissionsCRUD:
    """Tests para el CRUD completo de permisos."""

    async def test_create_permission(self, client: AsyncClient, admin_token: str):
        """Crear un permiso como superusuario."""
        response = await client.post(
            "/api/v1/permissions/",
            json={"name": "turnos:read", "description": "Leer turnos"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "turnos:read"
        assert data["description"] == "Leer turnos"
        assert "id" in data

    async def test_create_permission_duplicate(self, client: AsyncClient, admin_token: str):
        """No se puede crear un permiso con nombre duplicado."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        await client.post(
            "/api/v1/permissions/",
            json={"name": "dup:perm"},
            headers=headers,
        )
        response = await client.post(
            "/api/v1/permissions/",
            json={"name": "dup:perm"},
            headers=headers,
        )
        assert response.status_code == 409

    async def test_create_permission_unauthorized(self, client: AsyncClient, user_token: str):
        """Un usuario normal no puede crear permisos."""
        response = await client.post(
            "/api/v1/permissions/",
            json={"name": "test:perm"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    async def test_list_permissions(self, client: AsyncClient, admin_token: str):
        """Listar permisos."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        await client.post(
            "/api/v1/permissions/",
            json={"name": "list:test1"},
            headers=headers,
        )
        await client.post(
            "/api/v1/permissions/",
            json={"name": "list:test2"},
            headers=headers,
        )
        response = await client.get("/api/v1/permissions/", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) >= 2

    async def test_get_permission_by_id(self, client: AsyncClient, admin_token: str):
        """Obtener un permiso por ID."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        create_resp = await client.post(
            "/api/v1/permissions/",
            json={"name": "get:test"},
            headers=headers,
        )
        perm_id = create_resp.json()["id"]
        response = await client.get(f"/api/v1/permissions/{perm_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["name"] == "get:test"

    async def test_update_permission(self, client: AsyncClient, admin_token: str):
        """Actualizar un permiso."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        create_resp = await client.post(
            "/api/v1/permissions/",
            json={"name": "upd:test", "description": "Original"},
            headers=headers,
        )
        perm_id = create_resp.json()["id"]
        response = await client.patch(
            f"/api/v1/permissions/{perm_id}",
            json={"description": "Actualizado"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["description"] == "Actualizado"

    async def test_delete_permission(self, client: AsyncClient, admin_token: str):
        """Eliminar un permiso libre."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        create_resp = await client.post(
            "/api/v1/permissions/",
            json={"name": "del:test"},
            headers=headers,
        )
        perm_id = create_resp.json()["id"]
        response = await client.delete(f"/api/v1/permissions/{perm_id}", headers=headers)
        assert response.status_code == 204

        # Verificar que ya no existe
        response = await client.get(f"/api/v1/permissions/{perm_id}", headers=headers)
        assert response.status_code == 404

    async def test_delete_permission_assigned_to_role(self, client: AsyncClient, admin_token: str):
        """No se puede eliminar un permiso asignado a un rol."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # Crear permiso
        perm_resp = await client.post(
            "/api/v1/permissions/",
            json={"name": "nodelete:test"},
            headers=headers,
        )
        perm_id = perm_resp.json()["id"]

        # Crear rol con ese permiso
        await client.post(
            "/api/v1/roles/",
            json={"name": "test_role", "permission_ids": [perm_id]},
            headers=headers,
        )

        # Intentar eliminar el permiso → debe fallar
        response = await client.delete(f"/api/v1/permissions/{perm_id}", headers=headers)
        assert response.status_code == 409


@pytest.mark.asyncio
class TestRolesValidation:
    """Tests para validaciones de negocio en roles."""

    async def test_delete_role_with_users_fails(self, client: AsyncClient, admin_token: str):
        """No se puede eliminar un rol que tiene usuarios asignados."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # El rol 'admin' ya tiene al usuario testadmin asignado
        # Obtener el rol admin
        roles_resp = await client.get("/api/v1/roles/", headers=headers)
        admin_role = next(r for r in roles_resp.json() if r["name"] == "admin")

        # Intentar eliminar → debe fallar
        response = await client.delete(
            f"/api/v1/roles/{admin_role['id']}", headers=headers
        )
        assert response.status_code == 409
        assert "usuario(s) asignado(s)" in response.json()["detail"]

    async def test_delete_role_without_users_succeeds(self, client: AsyncClient, admin_token: str):
        """Sí se puede eliminar un rol sin usuarios."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        create_resp = await client.post(
            "/api/v1/roles/",
            json={"name": "empty_role"},
            headers=headers,
        )
        role_id = create_resp.json()["id"]

        response = await client.delete(f"/api/v1/roles/{role_id}", headers=headers)
        assert response.status_code == 204
