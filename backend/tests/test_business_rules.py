"""Tests para el módulo de Reglas de Negocio."""
import pytest
from datetime import date, timedelta
from httpx import AsyncClient


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════

async def _create_shift_type(client: AsyncClient, token: str, code: str, start: str, end: str, hours: int) -> dict:
    resp = await client.post(
        "/api/v1/shift-types/",
        json={
            "name": f"Turno {code}",
            "code": code,
            "start_time": start,
            "end_time": end,
            "duration_hours": hours,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_category(client: AsyncClient, token: str, name: str = "Cat Rules") -> dict:
    resp = await client.post(
        "/api/v1/employee-categories/",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_employee(
    client: AsyncClient, token: str, category_id: str,
    number: str = "R-001", document: str = "55000001",
) -> dict:
    resp = await client.post(
        "/api/v1/employees/",
        json={
            "employee_number": number,
            "first_name": "Carlos",
            "last_name": "García",
            "document_number": document,
            "hire_date": "2024-01-01",
            "category_id": category_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_assignment(
    client: AsyncClient, token: str,
    emp_id: str, st_id: str, target_date: str,
) -> dict:
    resp = await client.post(
        "/api/v1/assignments/",
        json={"date": target_date, "employee_id": emp_id, "shift_type_id": st_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ═══════════════════════════════════════════════════════════
#  Tests CRUD de Reglas de Negocio
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_business_rule(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/v1/business-rules/",
        json={
            "name": "Max 48h semanales",
            "description": "No superar las 48 horas semanales",
            "category": "horas",
            "max_value": 48,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Max 48h semanales"
    assert data["category"] == "horas"
    assert data["max_value"] == 48
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_list_business_rules(client: AsyncClient, admin_token: str):
    await client.post(
        "/api/v1/business-rules/",
        json={"name": "Regla listado", "category": "horas", "max_value": 40},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.get(
        "/api/v1/business-rules/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_update_business_rule(client: AsyncClient, admin_token: str):
    create = await client.post(
        "/api/v1/business-rules/",
        json={"name": "Regla update", "category": "dias_consecutivos", "max_value": 5},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    rule_id = create.json()["id"]

    resp = await client.patch(
        f"/api/v1/business-rules/{rule_id}",
        json={"max_value": 6, "is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["max_value"] == 6
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_delete_business_rule(client: AsyncClient, admin_token: str):
    create = await client.post(
        "/api/v1/business-rules/",
        json={"name": "Regla delete", "category": "descanso", "max_value": 12},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    rule_id = create.json()["id"]

    resp = await client.delete(
        f"/api/v1/business-rules/{rule_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_duplicate_rule_name_rejected(client: AsyncClient, admin_token: str):
    name = "Regla unica"
    await client.post(
        "/api/v1/business-rules/",
        json={"name": name, "category": "horas", "max_value": 40},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.post(
        "/api/v1/business-rules/",
        json={"name": name, "category": "horas", "max_value": 48},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


# ═══════════════════════════════════════════════════════════
#  Tests CRUD de Incompatibilidades
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_incompatibility(client: AsyncClient, admin_token: str):
    st_n = await _create_shift_type(client, admin_token, "NI", "22:00:00", "06:00:00", 8)
    st_m = await _create_shift_type(client, admin_token, "MI", "06:00:00", "14:00:00", 8)

    resp = await client.post(
        "/api/v1/shift-incompatibilities/",
        json={
            "shift_type_a_id": st_n["id"],
            "shift_type_b_id": st_m["id"],
            "direction": "siguiente",
            "description": "No se puede hacer Mañana después de Noche",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["shift_type_a_name"] == "Turno NI"
    assert data["shift_type_b_name"] == "Turno MI"


@pytest.mark.asyncio
async def test_incompatibility_same_shift_rejected(client: AsyncClient, admin_token: str):
    st = await _create_shift_type(client, admin_token, "XX", "06:00:00", "14:00:00", 8)
    resp = await client.post(
        "/api/v1/shift-incompatibilities/",
        json={"shift_type_a_id": st["id"], "shift_type_b_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_incompatibilities(client: AsyncClient, admin_token: str):
    st_a = await _create_shift_type(client, admin_token, "LA", "06:00:00", "14:00:00", 8)
    st_b = await _create_shift_type(client, admin_token, "LB", "14:00:00", "22:00:00", 8)
    await client.post(
        "/api/v1/shift-incompatibilities/",
        json={"shift_type_a_id": st_a["id"], "shift_type_b_id": st_b["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.get(
        "/api/v1/shift-incompatibilities/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_delete_incompatibility(client: AsyncClient, admin_token: str):
    st_a = await _create_shift_type(client, admin_token, "DA", "06:00:00", "14:00:00", 8)
    st_b = await _create_shift_type(client, admin_token, "DB", "14:00:00", "22:00:00", 8)
    create = await client.post(
        "/api/v1/shift-incompatibilities/",
        json={"shift_type_a_id": st_a["id"], "shift_type_b_id": st_b["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    inc_id = create.json()["id"]
    resp = await client.delete(
        f"/api/v1/shift-incompatibilities/{inc_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204


# ═══════════════════════════════════════════════════════════
#  Tests de Validación de Reglas en Asignaciones
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_max_weekly_hours_blocks_assignment(client: AsyncClient, admin_token: str):
    """Regla de horas semanales bloquea asignación que la exceda."""
    cat = await _create_category(client, admin_token, "Cat Horas")
    emp = await _create_employee(client, admin_token, cat["id"], "RH-001", "77000001")
    st = await _create_shift_type(client, admin_token, "WH", "06:00:00", "18:00:00", 12)

    # Regla: máximo 24h por semana (para facilitar el test)
    await client.post(
        "/api/v1/business-rules/",
        json={"name": "Max 24h semanal test", "category": "horas", "max_value": 24},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # El lunes de la próxima semana
    today = date.today()
    next_monday = today + timedelta(days=(7 - today.weekday()))

    # Asignar lunes (12h) y martes (12h) → total 24h
    r1 = await client.post(
        "/api/v1/assignments/",
        json={"date": next_monday.isoformat(), "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r1.status_code == 201

    r2 = await client.post(
        "/api/v1/assignments/",
        json={"date": (next_monday + timedelta(days=1)).isoformat(), "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r2.status_code == 201

    # Miércoles (12h más) → total 36h > 24h → debe fallar
    r3 = await client.post(
        "/api/v1/assignments/",
        json={"date": (next_monday + timedelta(days=2)).isoformat(), "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r3.status_code == 409
    assert "horas semanales" in r3.json()["detail"].lower()


@pytest.mark.asyncio
async def test_max_consecutive_days_blocks_assignment(client: AsyncClient, admin_token: str):
    """Regla de días consecutivos bloquea cuando se supera el límite."""
    cat = await _create_category(client, admin_token, "Cat Consec")
    emp = await _create_employee(client, admin_token, cat["id"], "RC-001", "77000002")
    st = await _create_shift_type(client, admin_token, "CD", "08:00:00", "16:00:00", 8)

    # Regla: máximo 3 días consecutivos
    await client.post(
        "/api/v1/business-rules/",
        json={"name": "Max 3 días consec test", "category": "dias_consecutivos", "max_value": 3},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    today = date.today()
    base = today + timedelta(days=100)  # Fechas lejanas para evitar conflictos

    # Asignar 3 días consecutivos
    for i in range(3):
        r = await client.post(
            "/api/v1/assignments/",
            json={"date": (base + timedelta(days=i)).isoformat(), "employee_id": emp["id"], "shift_type_id": st["id"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 201, f"Día {i}: {r.text}"

    # Cuarto día → debe fallar
    r4 = await client.post(
        "/api/v1/assignments/",
        json={"date": (base + timedelta(days=3)).isoformat(), "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r4.status_code == 409
    assert "consecutivos" in r4.json()["detail"].lower()


@pytest.mark.asyncio
async def test_weekly_rest_blocks_assignment(client: AsyncClient, admin_token: str):
    """Regla de descanso semanal bloquea cuando no quedan días libres suficientes."""
    cat = await _create_category(client, admin_token, "Cat Descanso")
    emp = await _create_employee(client, admin_token, cat["id"], "RD-001", "77000003")
    st = await _create_shift_type(client, admin_token, "WR", "08:00:00", "14:00:00", 6)

    # Regla: mínimo 2 días libres por semana
    await client.post(
        "/api/v1/business-rules/",
        json={"name": "Min 2 francos semanal", "category": "descanso_semanal", "max_value": 2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    today = date.today()
    # Buscar un lunes lejano
    base = today + timedelta(days=200)
    monday = base - timedelta(days=base.weekday())

    # Asignar lunes a viernes (5 días = solo 2 libres, sáb y dom)
    for i in range(5):
        r = await client.post(
            "/api/v1/assignments/",
            json={"date": (monday + timedelta(days=i)).isoformat(), "employee_id": emp["id"], "shift_type_id": st["id"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 201, f"Día {i}: {r.text}"

    # Sábado → solo quedaría 1 día libre (domingo) < 2 → debe fallar
    r6 = await client.post(
        "/api/v1/assignments/",
        json={"date": (monday + timedelta(days=5)).isoformat(), "employee_id": emp["id"], "shift_type_id": st["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r6.status_code == 409
    assert "libre" in r6.json()["detail"].lower()


@pytest.mark.asyncio
async def test_shift_incompatibility_blocks_assignment(client: AsyncClient, admin_token: str):
    """Incompatibilidad Noche → Mañana bloquea la asignación."""
    cat = await _create_category(client, admin_token, "Cat Incompat")
    emp = await _create_employee(client, admin_token, cat["id"], "RI-001", "77000004")
    st_noche = await _create_shift_type(client, admin_token, "SN", "22:00:00", "06:00:00", 8)
    st_man = await _create_shift_type(client, admin_token, "SM", "06:00:00", "14:00:00", 8)

    # Crear incompatibilidad: Noche → Mañana prohibido
    await client.post(
        "/api/v1/shift-incompatibilities/",
        json={
            "shift_type_a_id": st_noche["id"],
            "shift_type_b_id": st_man["id"],
            "direction": "siguiente",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    today = date.today()
    day1 = (today + timedelta(days=300)).isoformat()
    day2 = (today + timedelta(days=301)).isoformat()

    # Asignar noche el día 1
    r1 = await client.post(
        "/api/v1/assignments/",
        json={"date": day1, "employee_id": emp["id"], "shift_type_id": st_noche["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r1.status_code == 201

    # Intentar asignar mañana el día 2 → incompatible (o descanso insuficiente)
    r2 = await client.post(
        "/api/v1/assignments/",
        json={"date": day2, "employee_id": emp["id"], "shift_type_id": st_man["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r2.status_code == 409
    detail = r2.json()["detail"].lower()
    assert "incompatibilidad" in detail or "descanso" in detail


# ═══════════════════════════════════════════════════════════
#  Test de Endpoint de Validación Previa
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_validate_endpoint(client: AsyncClient, admin_token: str):
    """El endpoint de validación devuelve is_valid sin crear la asignación."""
    cat = await _create_category(client, admin_token, "Cat Validate")
    emp = await _create_employee(client, admin_token, cat["id"], "RV-001", "77000005")
    st = await _create_shift_type(client, admin_token, "VL", "08:00:00", "16:00:00", 8)

    target_date = (date.today() + timedelta(days=400)).isoformat()
    resp = await client.post(
        "/api/v1/assignments/validate",
        json={"employee_id": emp["id"], "shift_type_id": st["id"], "date": target_date},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["violations"] == []


@pytest.mark.asyncio
async def test_filter_rules_by_category(client: AsyncClient, admin_token: str):
    """Se puede filtrar reglas por categoría."""
    await client.post(
        "/api/v1/business-rules/",
        json={"name": "Filtro horas", "category": "horas", "max_value": 40},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        "/api/v1/business-rules/",
        json={"name": "Filtro consec", "category": "dias_consecutivos", "max_value": 5},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        "/api/v1/business-rules/?category=horas",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert all(r["category"] == "horas" for r in resp.json())
