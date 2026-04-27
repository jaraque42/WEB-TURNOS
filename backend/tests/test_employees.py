import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestEmployeeCategories:
    """Tests CRUD de categorías de empleado."""

    async def test_create_category(self, client: AsyncClient, admin_token: str):
        response = await client.post(
            "/api/v1/employee-categories/",
            json={"name": "Oficial", "description": "Oficiales"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Oficial"

    async def test_create_category_duplicate(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        await client.post("/api/v1/employee-categories/", json={"name": "Dup"}, headers=headers)
        resp = await client.post("/api/v1/employee-categories/", json={"name": "Dup"}, headers=headers)
        assert resp.status_code == 409

    async def test_list_categories(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        await client.post("/api/v1/employee-categories/", json={"name": "Cat1"}, headers=headers)
        resp = await client.get("/api/v1/employee-categories/", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_update_category(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        create = await client.post("/api/v1/employee-categories/", json={"name": "Editable"}, headers=headers)
        cat_id = create.json()["id"]
        resp = await client.patch(
            f"/api/v1/employee-categories/{cat_id}",
            json={"description": "Updated"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated"

    async def test_delete_category(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        create = await client.post("/api/v1/employee-categories/", json={"name": "Borrable"}, headers=headers)
        cat_id = create.json()["id"]
        resp = await client.delete(f"/api/v1/employee-categories/{cat_id}", headers=headers)
        assert resp.status_code == 204


@pytest.mark.asyncio
class TestAgentTypes:
    """Tests CRUD de tipos de agente."""

    async def test_create_agent_type(self, client: AsyncClient, admin_token: str):
        response = await client.post(
            "/api/v1/agent-types/",
            json={"name": "Patrullero", "description": "Agente de patrullaje"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Patrullero"

    async def test_list_agent_types(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        await client.post("/api/v1/agent-types/", json={"name": "Despachante"}, headers=headers)
        resp = await client.get("/api/v1/agent-types/", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


@pytest.mark.asyncio
class TestEmployees:
    """Tests CRUD de empleados."""

    async def _create_employee(self, client: AsyncClient, headers: dict, **overrides):
        data = {
            "employee_number": "EMP-001",
            "first_name": "Juan",
            "last_name": "Pérez",
            "document_number": "12345678",
            "phone": "+54 11 1234-5678",
            "hire_date": "2024-01-15",
        }
        data.update(overrides)
        return await client.post("/api/v1/employees/", json=data, headers=headers)

    async def test_create_employee(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = await self._create_employee(client, headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["first_name"] == "Juan"
        assert data["last_name"] == "Pérez"
        assert data["status"] == "activo"

    async def test_create_employee_duplicate_number(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        await self._create_employee(client, headers, employee_number="DUP-001", document_number="11111111")
        resp = await self._create_employee(client, headers, employee_number="DUP-001", document_number="22222222")
        assert resp.status_code == 409

    async def test_create_employee_duplicate_document(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        await self._create_employee(client, headers, employee_number="UNQ-001", document_number="99999999")
        resp = await self._create_employee(client, headers, employee_number="UNQ-002", document_number="99999999")
        assert resp.status_code == 409

    async def test_list_employees(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        await self._create_employee(client, headers, employee_number="LST-001", document_number="33333333")
        resp = await client.get("/api/v1/employees/", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_get_employee_detail(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        create = await self._create_employee(client, headers, employee_number="DTL-001", document_number="44444444")
        emp_id = create.json()["id"]
        resp = await client.get(f"/api/v1/employees/{emp_id}", headers=headers)
        assert resp.status_code == 200
        assert "licenses" in resp.json()

    async def test_update_employee(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        create = await self._create_employee(client, headers, employee_number="UPD-001", document_number="55555555")
        emp_id = create.json()["id"]
        resp = await client.patch(
            f"/api/v1/employees/{emp_id}",
            json={"phone": "+54 11 9999-0000", "status": "inactivo"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["phone"] == "+54 11 9999-0000"
        assert resp.json()["status"] == "inactivo"

    async def test_delete_employee(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        create = await self._create_employee(client, headers, employee_number="DEL-001", document_number="66666666")
        emp_id = create.json()["id"]
        resp = await client.delete(f"/api/v1/employees/{emp_id}", headers=headers)
        assert resp.status_code == 204

    async def test_cannot_delete_employee_with_assignments(self, client: AsyncClient, admin_token: str):
        # Un empleado con al menos una asignación no puede eliminarse
        headers = {"Authorization": f"Bearer {admin_token}"}
        create = await self._create_employee(client, headers, employee_number="DEL-ASSIGN-001", document_number="77777777")
        emp_id = create.json()["id"]
        # crear categoría y turno para generar la asignación
        # (el helper de este archivo no define métodos, así creamos directamente)
        st_resp = await client.post(
            "/api/v1/shift-types/",
            json={
                "name": "Turno X",
                "code": "X",
                "start_time": "08:00:00",
                "end_time": "16:00:00",
                "duration_hours": 8,
            },
            headers=headers,
        )
        assert st_resp.status_code == 201
        st_id = st_resp.json()["id"]

        # generar asignación en una fecha futura
        from datetime import date, timedelta
        target_date = (date.today() + timedelta(days=1)).isoformat()
        assign_resp = await client.post(
            "/api/v1/assignments/",
            json={"date": target_date, "employee_id": emp_id, "shift_type_id": st_id},
            headers=headers,
        )
        assert assign_resp.status_code == 201

        # intentar eliminar el empleado
        resp = await client.delete(f"/api/v1/employees/{emp_id}", headers=headers)
        assert resp.status_code == 409

    async def test_bulk_delete_with_assignments(self, client: AsyncClient, admin_token: str):
        # sólo superusuario puede, usare admin_token as superuser
        headers = {"Authorization": f"Bearer {admin_token}"}
        # crear dos empleados
        emp1 = await self._create_employee(client, headers, employee_number="BULK1", document_number="88888888")
        emp2 = await self._create_employee(client, headers, employee_number="BULK2", document_number="99999999")
        ids = [emp1.json()["id"], emp2.json()["id"]]
        # asignar turno al primer empleado
        st_resp = await client.post(
            "/api/v1/shift-types/",
            json={
                "name": "Turno Y",
                "code": "Y",
                "start_time": "08:00:00",
                "end_time": "16:00:00",
                "duration_hours": 8,
            },
            headers=headers,
        )
        assert st_resp.status_code == 201
        st_id = st_resp.json()["id"]
        from datetime import date, timedelta
        target_date = (date.today() + timedelta(days=1)).isoformat()
        resp_assign = await client.post(
            "/api/v1/assignments/",
            json={"date": target_date, "employee_id": ids[0], "shift_type_id": st_id},
            headers=headers,
        )
        assert resp_assign.status_code == 201
        # intentar bulk delete
        bulk_resp = await client.post(
            "/api/v1/employees/bulk-delete",
            json=ids,
            headers=headers,
        )
        assert bulk_resp.status_code == 409

    async def test_create_employee_with_category(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        cat = await client.post("/api/v1/employee-categories/", json={"name": "TestCat"}, headers=headers)
        resp = await self._create_employee(
            client, headers,
            employee_number="CAT-001",
            document_number="77777777",
            category_id=cat.json()["id"],
        )
        assert resp.status_code == 201
        assert resp.json()["category"]["name"] == "TestCat"

    async def test_filter_by_status(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        await self._create_employee(client, headers, employee_number="FIL-001", document_number="88888888")
        resp = await client.get("/api/v1/employees/?status=activo", headers=headers)
        assert resp.status_code == 200
        for emp in resp.json():
            assert emp["status"] == "activo"


@pytest.mark.asyncio
class TestLicenses:
    """Tests CRUD de licencias."""

    async def _setup_employee(self, client: AsyncClient, headers: dict):
        resp = await client.post(
            "/api/v1/employees/",
            json={
                "employee_number": f"LIC-{id(self)}",
                "first_name": "Licencia",
                "last_name": "Test",
                "document_number": f"LIC{id(self)}",
                "hire_date": "2024-01-01",
            },
            headers=headers,
        )
        return resp.json()["id"]

    async def test_create_license(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        emp_id = await self._setup_employee(client, headers)
        resp = await client.post(
            "/api/v1/licenses/",
            json={
                "license_type": "vacaciones",
                "start_date": "2026-03-01",
                "end_date": "2026-03-15",
                "reason": "Vacaciones anuales",
                "employee_id": emp_id,
            },
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["license_type"] == "vacaciones"
        assert resp.json()["status"] == "pendiente"

    async def test_create_license_invalid_dates(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        emp_id = await self._setup_employee(client, headers)
        resp = await client.post(
            "/api/v1/licenses/",
            json={
                "license_type": "enfermedad",
                "start_date": "2026-03-15",
                "end_date": "2026-03-01",
                "employee_id": emp_id,
            },
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_list_employee_licenses(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        emp_id = await self._setup_employee(client, headers)
        await client.post(
            "/api/v1/licenses/",
            json={
                "license_type": "personal",
                "start_date": "2026-04-01",
                "end_date": "2026-04-05",
                "employee_id": emp_id,
            },
            headers=headers,
        )
        resp = await client.get(f"/api/v1/employees/{emp_id}/licenses/", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_update_license_status(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        emp_id = await self._setup_employee(client, headers)
        create = await client.post(
            "/api/v1/licenses/",
            json={
                "license_type": "estudio",
                "start_date": "2026-05-01",
                "end_date": "2026-05-10",
                "employee_id": emp_id,
            },
            headers=headers,
        )
        lic_id = create.json()["id"]
        resp = await client.patch(
            f"/api/v1/licenses/{lic_id}",
            json={"status": "aprobada"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "aprobada"

    async def test_delete_license(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        emp_id = await self._setup_employee(client, headers)
        create = await client.post(
            "/api/v1/licenses/",
            json={
                "license_type": "otro",
                "start_date": "2026-06-01",
                "end_date": "2026-06-03",
                "employee_id": emp_id,
            },
            headers=headers,
        )
        lic_id = create.json()["id"]
        resp = await client.delete(f"/api/v1/licenses/{lic_id}", headers=headers)
        assert resp.status_code == 204

    async def test_delete_employee_cascades_licenses(self, client: AsyncClient, admin_token: str):
        """Al eliminar un empleado, sus licencias se eliminan también."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        emp_id = await self._setup_employee(client, headers)
        create = await client.post(
            "/api/v1/licenses/",
            json={
                "license_type": "vacaciones",
                "start_date": "2026-07-01",
                "end_date": "2026-07-15",
                "employee_id": emp_id,
            },
            headers=headers,
        )
        lic_id = create.json()["id"]

        # Eliminar empleado
        await client.delete(f"/api/v1/employees/{emp_id}", headers=headers)

        # La licencia ya no debe existir
        resp = await client.get(f"/api/v1/licenses/{lic_id}", headers=headers)
        assert resp.status_code == 404
