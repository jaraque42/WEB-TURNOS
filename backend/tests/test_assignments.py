"""Tests para el módulo de Asignaciones de Turnos."""
import pytest
import pytest_asyncio
from datetime import date, timedelta
from httpx import AsyncClient


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════

async def _create_shift_type(client: AsyncClient, token: str, code: str = "M") -> dict:
    resp = await client.post(
        "/api/v1/shift-types/",
        json={
            "name": f"Turno {code}",
            "code": code,
            "start_time": "06:00:00",
            "end_time": "14:00:00",
            "duration_hours": 8,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_category(client: AsyncClient, token: str) -> dict:
    resp = await client.post(
        "/api/v1/employee-categories/",
        json={"name": "Cat Test Asig"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_employee(
    client: AsyncClient, token: str, category_id: str,
    number: str = "EMP-001", document: str = "11111111",
) -> dict:
    resp = await client.post(
        "/api/v1/employees/",
        json={
            "employee_number": number,
            "first_name": "Juan",
            "last_name": "Pérez",
            "document_number": document,
            "hire_date": "2024-01-01",
            "category_id": category_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ═══════════════════════════════════════════════════════════
#  Tests de Asignaciones CRUD
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_assignment(client: AsyncClient, admin_token: str):
    cat = await _create_category(client, admin_token)
    emp = await _create_employee(client, admin_token, cat["id"])
    st = await _create_shift_type(client, admin_token)

    target_date = (date.today() + timedelta(days=1)).isoformat()
    resp = await client.post(
        "/api/v1/assignments/",
        json={
            "date": target_date,
            "employee_id": emp["id"],
            "shift_type_id": st["id"],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["date"] == target_date
    assert data["status"] == "asignado"
    assert data["employee_name"] == "Pérez, Juan"
    assert data["shift_type_name"] == "Turno M"


@pytest.mark.asyncio
async def test_list_assignments(client: AsyncClient, admin_token: str):
    cat = await _create_category(client, admin_token)
    emp = await _create_employee(client, admin_token, cat["id"])
    st = await _create_shift_type(client, admin_token)

    target_date = (date.today() + timedelta(days=1)).isoformat()
    await client.post(
        "/api/v1/assignments/",
        json={"date": target_date, "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        "/api/v1/assignments/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_assignment_by_id(client: AsyncClient, admin_token: str):
    cat = await _create_category(client, admin_token)
    emp = await _create_employee(client, admin_token, cat["id"])
    st = await _create_shift_type(client, admin_token)

    target_date = (date.today() + timedelta(days=1)).isoformat()
    create_resp = await client.post(
        "/api/v1/assignments/",
        json={"date": target_date, "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    aid = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/assignments/{aid}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == aid


@pytest.mark.asyncio
async def test_update_assignment_status(client: AsyncClient, admin_token: str):
    cat = await _create_category(client, admin_token)
    emp = await _create_employee(client, admin_token, cat["id"])
    st = await _create_shift_type(client, admin_token)

    target_date = (date.today() + timedelta(days=1)).isoformat()
    create_resp = await client.post(
        "/api/v1/assignments/",
        json={"date": target_date, "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    aid = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/assignments/{aid}",
        json={"status": "confirmado"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmado"


@pytest.mark.asyncio
async def test_cancel_assignment(client: AsyncClient, admin_token: str):
    cat = await _create_category(client, admin_token)
    emp = await _create_employee(client, admin_token, cat["id"])
    st = await _create_shift_type(client, admin_token)

    target_date = (date.today() + timedelta(days=1)).isoformat()
    create_resp = await client.post(
        "/api/v1/assignments/",
        json={"date": target_date, "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    aid = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/assignments/{aid}",
        json={"status": "cancelado"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelado"


@pytest.mark.asyncio
async def test_delete_assignment(client: AsyncClient, admin_token: str):
    cat = await _create_category(client, admin_token)
    emp = await _create_employee(client, admin_token, cat["id"])
    st = await _create_shift_type(client, admin_token)

    target_date = (date.today() + timedelta(days=1)).isoformat()
    create_resp = await client.post(
        "/api/v1/assignments/",
        json={"date": target_date, "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    aid = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/assignments/{aid}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204


# ═══════════════════════════════════════════════════════════
#  Tests de Reglas de Negocio
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_duplicate_assignment_same_date(client: AsyncClient, admin_token: str):
    """No se puede asignar el mismo empleado dos veces en la misma fecha."""
    cat = await _create_category(client, admin_token)
    emp = await _create_employee(client, admin_token, cat["id"])
    st = await _create_shift_type(client, admin_token)

    target_date = (date.today() + timedelta(days=1)).isoformat()
    resp1 = await client.post(
        "/api/v1/assignments/",
        json={"date": target_date, "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        "/api/v1/assignments/",
        json={"date": target_date, "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_assignment_inactive_employee(client: AsyncClient, admin_token: str):
    """No se puede asignar turno a un empleado inactivo."""
    cat = await _create_category(client, admin_token)
    emp = await _create_employee(client, admin_token, cat["id"])
    st = await _create_shift_type(client, admin_token)

    # Desactivar empleado
    await client.patch(
        f"/api/v1/employees/{emp['id']}",
        json={"status": "inactivo"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    target_date = (date.today() + timedelta(days=1)).isoformat()
    resp = await client.post(
        "/api/v1/assignments/",
        json={"date": target_date, "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409
    assert "activo" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_assignment_on_leave(client: AsyncClient, admin_token: str):
    """No se puede asignar turno si el empleado tiene licencia aprobada."""
    cat = await _create_category(client, admin_token)
    emp = await _create_employee(client, admin_token, cat["id"])
    st = await _create_shift_type(client, admin_token)

    target_date = date.today() + timedelta(days=5)

    # Crear licencia aprobada que cubre la fecha
    lic_resp = await client.post(
        "/api/v1/licenses/",
        json={
            "employee_id": emp["id"],
            "license_type": "vacaciones",
            "start_date": (target_date - timedelta(days=1)).isoformat(),
            "end_date": (target_date + timedelta(days=5)).isoformat(),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert lic_resp.status_code == 201
    lic_id = lic_resp.json()["id"]

    # Aprobar la licencia
    await client.patch(
        f"/api/v1/licenses/{lic_id}",
        json={"status": "aprobada"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.post(
        "/api/v1/assignments/",
        json={"date": target_date.isoformat(), "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409
    assert "licencia" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cannot_delete_completed_assignment(client: AsyncClient, admin_token: str):
    """No se puede eliminar una asignación completada."""
    cat = await _create_category(client, admin_token)
    emp = await _create_employee(client, admin_token, cat["id"])
    st = await _create_shift_type(client, admin_token)

    target_date = (date.today() + timedelta(days=1)).isoformat()
    create_resp = await client.post(
        "/api/v1/assignments/",
        json={"date": target_date, "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    aid = create_resp.json()["id"]

    # Marcar como completada
    await client.patch(
        f"/api/v1/assignments/{aid}",
        json={"status": "completado"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.delete(
        f"/api/v1/assignments/{aid}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


# ═══════════════════════════════════════════════════════════
#  Tests de Generación Masiva
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_bulk_create_assignments(client: AsyncClient, admin_token: str):
    cat = await _create_category(client, admin_token)
    emp1 = await _create_employee(client, admin_token, cat["id"], "EMP-B1", "99000001")
    emp2 = await _create_employee(client, admin_token, cat["id"], "EMP-B2", "99000002")
    st = await _create_shift_type(client, admin_token)

    start = date.today() + timedelta(days=10)
    end = start + timedelta(days=2)  # 3 días

    resp = await client.post(
        "/api/v1/assignments/bulk",
        json={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "employee_ids": [emp1["id"], emp2["id"]],
            "shift_type_id": st["id"],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["created"] == 6  # 3 días × 2 empleados
    assert data["skipped"] == 0


@pytest.mark.asyncio
async def test_bulk_skips_duplicates(client: AsyncClient, admin_token: str):
    """La generación masiva salta asignaciones que ya existen."""
    cat = await _create_category(client, admin_token)
    emp = await _create_employee(client, admin_token, cat["id"])
    st = await _create_shift_type(client, admin_token)

    target_date = date.today() + timedelta(days=20)

    # Crear una asignación individual
    await client.post(
        "/api/v1/assignments/",
        json={"date": target_date.isoformat(), "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Intentar bulk que incluye esa fecha
    resp = await client.post(
        "/api/v1/assignments/bulk",
        json={
            "start_date": target_date.isoformat(),
            "end_date": (target_date + timedelta(days=1)).isoformat(),
            "employee_ids": [emp["id"]],
            "shift_type_id": st["id"],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["skipped"] >= 1
    assert data["created"] >= 1


# ═══════════════════════════════════════════════════════════
#  Tests de Permutas
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_swap_request_lifecycle(client: AsyncClient, admin_token: str):
    """Crear y aprobar una permuta intercambia los empleados."""
    cat = await _create_category(client, admin_token)
    emp1 = await _create_employee(client, admin_token, cat["id"], "EMP-S1", "88000001")
    emp2 = await _create_employee(client, admin_token, cat["id"], "EMP-S2", "88000002")
    st = await _create_shift_type(client, admin_token)

    d1 = (date.today() + timedelta(days=30)).isoformat()
    d2 = (date.today() + timedelta(days=31)).isoformat()

    a1 = await client.post(
        "/api/v1/assignments/",
        json={"date": d1, "employee_id": emp1["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    a2 = await client.post(
        "/api/v1/assignments/",
        json={"date": d2, "employee_id": emp2["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    a1_id = a1.json()["id"]
    a2_id = a2.json()["id"]

    # Crear solicitud de permuta
    swap_resp = await client.post(
        "/api/v1/swap-requests/",
        json={
            "requester_assignment_id": a1_id,
            "target_assignment_id": a2_id,
            "reason": "Motivo personal",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert swap_resp.status_code == 201
    swap = swap_resp.json()
    assert swap["status"] == "pendiente"

    # Aprobar la permuta
    resolve_resp = await client.patch(
        f"/api/v1/swap-requests/{swap['id']}",
        json={"status": "aprobado"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "aprobado"

    # Verificar que los empleados se intercambiaron
    check_a1 = await client.get(
        f"/api/v1/assignments/{a1_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    check_a2 = await client.get(
        f"/api/v1/assignments/{a2_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert check_a1.json()["employee_id"] == emp2["id"]
    assert check_a2.json()["employee_id"] == emp1["id"]


@pytest.mark.asyncio
async def test_swap_request_self_swap_rejected(client: AsyncClient, admin_token: str):
    """No se puede permutar con uno mismo."""
    cat = await _create_category(client, admin_token)
    emp = await _create_employee(client, admin_token, cat["id"])
    st = await _create_shift_type(client, admin_token)

    d1 = (date.today() + timedelta(days=40)).isoformat()
    d2 = (date.today() + timedelta(days=41)).isoformat()

    a1 = await client.post(
        "/api/v1/assignments/",
        json={"date": d1, "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    a2 = await client.post(
        "/api/v1/assignments/",
        json={"date": d2, "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    swap_resp = await client.post(
        "/api/v1/swap-requests/",
        json={
            "requester_assignment_id": a1.json()["id"],
            "target_assignment_id": a2.json()["id"],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert swap_resp.status_code == 409


# ═══════════════════════════════════════════════════════════
#  Tests de Estadísticas
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_assignment_stats(client: AsyncClient, admin_token: str):
    cat = await _create_category(client, admin_token)
    emp = await _create_employee(client, admin_token, cat["id"])
    st = await _create_shift_type(client, admin_token)

    target_date = date.today() + timedelta(days=50)
    await client.post(
        "/api/v1/assignments/",
        json={"date": target_date.isoformat(), "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        "/api/v1/assignments/stats",
        params={
            "date_from": target_date.isoformat(),
            "date_to": (target_date + timedelta(days=5)).isoformat(),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_assignments"] >= 1
    assert data["employees_assigned"] >= 1


# ═══════════════════════════════════════════════════════════
#  Tests de Filtros
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_filter_assignments_by_date(client: AsyncClient, admin_token: str):
    cat = await _create_category(client, admin_token)
    emp = await _create_employee(client, admin_token, cat["id"])
    st = await _create_shift_type(client, admin_token)

    target_date = date.today() + timedelta(days=60)
    await client.post(
        "/api/v1/assignments/",
        json={"date": target_date.isoformat(), "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        "/api/v1/assignments/",
        params={"date_from": target_date.isoformat(), "date_to": target_date.isoformat()},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert all(a["date"] == target_date.isoformat() for a in resp.json())


@pytest.mark.asyncio
async def test_filter_assignments_by_employee(client: AsyncClient, admin_token: str):
    cat = await _create_category(client, admin_token)
    emp = await _create_employee(client, admin_token, cat["id"])
    st = await _create_shift_type(client, admin_token)

    target_date = date.today() + timedelta(days=70)
    await client.post(
        "/api/v1/assignments/",
        json={"date": target_date.isoformat(), "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        "/api/v1/assignments/",
        params={"employee_id": emp["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert all(a["employee_id"] == emp["id"] for a in resp.json())
