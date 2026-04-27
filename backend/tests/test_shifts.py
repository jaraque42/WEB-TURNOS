import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestShiftTypes:
    """Tests CRUD de tipos de turno."""

    SHIFT_DATA = {
        "name": "Mañana",
        "code": "M",
        "description": "Turno de mañana",
        "start_time": "06:00:00",
        "end_time": "14:00:00",
        "duration_hours": 8,
        "color": "#4CAF50",
    }

    async def _create_shift_type(self, client: AsyncClient, headers: dict, **overrides):
        data = {**self.SHIFT_DATA, **overrides}
        return await client.post("/api/v1/shift-types/", json=data, headers=headers)

    async def test_create_shift_type(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = await self._create_shift_type(client, headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Mañana"
        assert data["code"] == "M"
        assert data["duration_hours"] == 8
        assert data["color"] == "#4CAF50"
        assert data["is_active"] is True

    async def test_create_shift_type_duplicate_name(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        await self._create_shift_type(client, headers, name="DupName", code="D1")
        resp = await self._create_shift_type(client, headers, name="DupName", code="D2")
        assert resp.status_code == 409

    async def test_create_shift_type_duplicate_code(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        await self._create_shift_type(client, headers, name="Turno1", code="DUP")
        resp = await self._create_shift_type(client, headers, name="Turno2", code="DUP")
        assert resp.status_code == 409

    async def test_list_shift_types(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        await self._create_shift_type(client, headers, name="Lista1", code="L1")
        resp = await client.get("/api/v1/shift-types/", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_list_active_only(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        create = await self._create_shift_type(client, headers, name="Inactivo", code="IN")
        st_id = create.json()["id"]
        await client.patch(f"/api/v1/shift-types/{st_id}", json={"is_active": False}, headers=headers)

        resp = await client.get("/api/v1/shift-types/?active_only=true", headers=headers)
        ids = [s["id"] for s in resp.json()]
        assert st_id not in ids

    async def test_get_shift_type(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        create = await self._create_shift_type(client, headers, name="GetMe", code="GM")
        st_id = create.json()["id"]
        resp = await client.get(f"/api/v1/shift-types/{st_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == "GM"

    async def test_update_shift_type(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        create = await self._create_shift_type(client, headers, name="Editable", code="ED")
        st_id = create.json()["id"]
        resp = await client.patch(
            f"/api/v1/shift-types/{st_id}",
            json={"duration_hours": 12, "color": "#FF0000"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["duration_hours"] == 12
        assert resp.json()["color"] == "#FF0000"

    async def test_delete_shift_type(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        create = await self._create_shift_type(client, headers, name="Borrable", code="BR")
        st_id = create.json()["id"]
        resp = await client.delete(f"/api/v1/shift-types/{st_id}", headers=headers)
        assert resp.status_code == 204

    async def test_delete_shift_type_with_coverage_fails(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        create = await self._create_shift_type(client, headers, name="ConCob", code="CC")
        st_id = create.json()["id"]

        # Crear cobertura asociada
        await client.post(
            "/api/v1/coverage/",
            json={"date": "2026-04-01", "min_employees": 3, "shift_type_id": st_id},
            headers=headers,
        )

        resp = await client.delete(f"/api/v1/shift-types/{st_id}", headers=headers)
        assert resp.status_code == 409


@pytest.mark.asyncio
class TestCoverageRequirements:
    """Tests CRUD de requerimientos de cobertura."""

    async def _create_shift_and_coverage(self, client: AsyncClient, headers: dict, shift_code: str):
        st_resp = await client.post(
            "/api/v1/shift-types/",
            json={
                "name": f"Turno-{shift_code}",
                "code": shift_code,
                "start_time": "06:00:00",
                "end_time": "14:00:00",
                "duration_hours": 8,
            },
            headers=headers,
        )
        st_id = st_resp.json()["id"]
        cov_resp = await client.post(
            "/api/v1/coverage/",
            json={"date": "2026-05-01", "min_employees": 5, "shift_type_id": st_id},
            headers=headers,
        )
        return st_id, cov_resp

    async def test_create_coverage(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        _, cov_resp = await self._create_shift_and_coverage(client, headers, "CV1")
        assert cov_resp.status_code == 201
        data = cov_resp.json()
        assert data["min_employees"] == 5
        assert data["shift_type"]["code"] == "CV1"

    async def test_create_coverage_invalid_max(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        st_resp = await client.post(
            "/api/v1/shift-types/",
            json={"name": "MaxTest", "code": "MX", "start_time": "06:00:00", "end_time": "14:00:00", "duration_hours": 8},
            headers=headers,
        )
        st_id = st_resp.json()["id"]
        resp = await client.post(
            "/api/v1/coverage/",
            json={"date": "2026-05-01", "min_employees": 10, "max_employees": 5, "shift_type_id": st_id},
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_list_coverage_with_date_filter(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        st_resp = await client.post(
            "/api/v1/shift-types/",
            json={"name": "FilterST", "code": "FS", "start_time": "06:00:00", "end_time": "14:00:00", "duration_hours": 8},
            headers=headers,
        )
        st_id = st_resp.json()["id"]

        for day in ["2026-06-01", "2026-06-02", "2026-06-03"]:
            await client.post(
                "/api/v1/coverage/",
                json={"date": day, "min_employees": 2, "shift_type_id": st_id},
                headers=headers,
            )

        resp = await client.get(
            "/api/v1/coverage/?start_date=2026-06-01&end_date=2026-06-02",
            headers=headers,
        )
        assert resp.status_code == 200
        dates = [c["date"] for c in resp.json()]
        assert "2026-06-03" not in dates

    async def test_update_coverage(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        _, cov_resp = await self._create_shift_and_coverage(client, headers, "UP1")
        cov_id = cov_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/coverage/{cov_id}",
            json={"min_employees": 8, "location": "Sede Central"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["min_employees"] == 8
        assert resp.json()["location"] == "Sede Central"

    async def test_delete_coverage(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        _, cov_resp = await self._create_shift_and_coverage(client, headers, "DL1")
        cov_id = cov_resp.json()["id"]

        resp = await client.delete(f"/api/v1/coverage/{cov_id}", headers=headers)
        assert resp.status_code == 204


@pytest.mark.asyncio
class TestBulkCoverage:
    """Tests para creación masiva de coberturas."""

    async def test_bulk_create(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Crear 2 tipos de turno
        st1 = await client.post(
            "/api/v1/shift-types/",
            json={"name": "BulkM", "code": "BM", "start_time": "06:00:00", "end_time": "14:00:00", "duration_hours": 8},
            headers=headers,
        )
        st2 = await client.post(
            "/api/v1/shift-types/",
            json={"name": "BulkT", "code": "BT", "start_time": "14:00:00", "end_time": "22:00:00", "duration_hours": 8},
            headers=headers,
        )

        resp = await client.post(
            "/api/v1/coverage/bulk/",
            json={
                "start_date": "2026-07-01",
                "end_date": "2026-07-03",
                "shift_type_ids": [st1.json()["id"], st2.json()["id"]],
                "min_employees": 4,
                "location": "Punto Norte",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        # 3 días × 2 turnos = 6 coberturas
        assert len(resp.json()) == 6

    async def test_bulk_create_invalid_dates(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        st = await client.post(
            "/api/v1/shift-types/",
            json={"name": "BulkErr", "code": "BE", "start_time": "06:00:00", "end_time": "14:00:00", "duration_hours": 8},
            headers=headers,
        )
        resp = await client.post(
            "/api/v1/coverage/bulk/",
            json={
                "start_date": "2026-07-05",
                "end_date": "2026-07-01",
                "shift_type_ids": [st.json()["id"]],
                "min_employees": 2,
            },
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_bulk_create_skips_duplicates(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        st = await client.post(
            "/api/v1/shift-types/",
            json={"name": "BulkDup", "code": "BD", "start_time": "06:00:00", "end_time": "14:00:00", "duration_hours": 8},
            headers=headers,
        )
        st_id = st.json()["id"]

        # Primera vez: crea 2
        resp1 = await client.post(
            "/api/v1/coverage/bulk/",
            json={
                "start_date": "2026-08-01",
                "end_date": "2026-08-02",
                "shift_type_ids": [st_id],
                "min_employees": 3,
            },
            headers=headers,
        )
        assert len(resp1.json()) == 2

        # Segunda vez: no crea duplicados
        resp2 = await client.post(
            "/api/v1/coverage/bulk/",
            json={
                "start_date": "2026-08-01",
                "end_date": "2026-08-02",
                "shift_type_ids": [st_id],
                "min_employees": 3,
            },
            headers=headers,
        )
        assert len(resp2.json()) == 0
