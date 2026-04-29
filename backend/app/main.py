from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, Base, reset_vercel_oidc_token, set_vercel_oidc_token
from app.core.security import get_password_hash
from app.routers import auth, users, roles, permissions, employees, shifts, assignments, business_rules, imports, system

# Importar modelos para que Alembic los detecte
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # En entorno serverless el lifespan puede fallar si la BD no está lista.
    # Lo envolvemos en try/except para que la función no crashee al arrancar.
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await seed_initial_data()
    except Exception as e:
        print(f"⚠️ ADVERTENCIA: No se pudo inicializar la BD al arrancar: {e}")
        print("Usa /api/v1/system/setup-db para inicializarla manualmente.")
    yield


async def seed_initial_data():
    """Crea el usuario admin y roles básicos si no existen."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.core.database import AsyncSessionLocal
    from app.models.user import User
    from app.models.role import Role
    from app.models.role import Permission

    # Permisos iniciales del sistema
    INITIAL_PERMISSIONS = [
        ("users:read", "Ver listado de usuarios"),
        ("users:create", "Crear usuarios"),
        ("users:update", "Actualizar usuarios"),
        ("users:delete", "Eliminar usuarios"),
        ("roles:read", "Ver listado de roles"),
        ("roles:create", "Crear roles"),
        ("roles:update", "Actualizar roles"),
        ("roles:delete", "Eliminar roles"),
        ("permissions:read", "Ver listado de permisos"),
        ("permissions:manage", "Crear, editar y eliminar permisos"),
        ("employees:read", "Ver listado de empleados"),
        ("employees:create", "Crear empleados"),
        ("employees:update", "Actualizar empleados y licencias"),
        ("employees:delete", "Eliminar empleados"),
        ("shifts:read", "Ver tipos de turno y coberturas"),
        ("shifts:create", "Crear tipos de turno y coberturas"),
        ("shifts:update", "Actualizar tipos de turno y coberturas"),
        ("shifts:delete", "Eliminar tipos de turno y coberturas"),
        ("assignments:read", "Ver asignaciones de turnos"),
        ("assignments:create", "Crear asignaciones de turnos"),
        ("assignments:update", "Actualizar asignaciones y permutas"),
        ("assignments:delete", "Eliminar asignaciones de turnos"),
        ("rules:read", "Ver reglas de negocio e incompatibilidades"),
        ("rules:manage", "Crear, editar y eliminar reglas de negocio"),
    ]

    async with AsyncSessionLocal() as db:
        # Crear permisos iniciales
        all_permissions = []
        for perm_name, perm_desc in INITIAL_PERMISSIONS:
            result = await db.execute(
                select(Permission).where(Permission.name == perm_name)
            )
            perm = result.scalar_one_or_none()
            if not perm:
                perm = Permission(name=perm_name, description=perm_desc)
                db.add(perm)
            all_permissions.append(perm)
        await db.commit()

        # Refrescar para tener los IDs
        for perm in all_permissions:
            await db.refresh(perm)

        # Crear rol admin si no existe y asignarle todos los permisos
        result = await db.execute(
            select(Role).options(selectinload(Role.permissions)).where(Role.name == "admin")
        )
        admin_role = result.scalar_one_or_none()
        if not admin_role:
            admin_role = Role(
                name="admin",
                description="Administrador del sistema",
                permissions=all_permissions,
            )
            db.add(admin_role)
        else:
            # Actualizar permisos del rol admin si le faltan
            existing_perm_names = {p.name for p in admin_role.permissions}
            for perm in all_permissions:
                if perm.name not in existing_perm_names:
                    admin_role.permissions.append(perm)

        # Crear rol operador con permisos de lectura
        result = await db.execute(
            select(Role).options(selectinload(Role.permissions)).where(Role.name == "operador")
        )
        operador_role = result.scalar_one_or_none()
        read_perms = [p for p in all_permissions if p.name.endswith(":read")]
        if not operador_role:
            db.add(Role(
                name="operador",
                description="Operador con acceso de lectura",
                permissions=read_perms,
            ))
        else:
            existing_perm_names = {p.name for p in operador_role.permissions}
            for perm in read_perms:
                if perm.name not in existing_perm_names:
                    operador_role.permissions.append(perm)

        # Crear rol supervisor con permisos de lectura + update
        result = await db.execute(
            select(Role).options(selectinload(Role.permissions)).where(Role.name == "supervisor")
        )
        supervisor_role = result.scalar_one_or_none()
        supervisor_perms = [
            p for p in all_permissions
            if p.name.endswith(":read") or p.name.endswith(":update")
        ]
        if not supervisor_role:
            db.add(Role(
                name="supervisor",
                description="Supervisor de turnos",
                permissions=supervisor_perms,
            ))
        else:
            existing_perm_names = {p.name for p in supervisor_role.permissions}
            for perm in supervisor_perms:
                if perm.name not in existing_perm_names:
                    supervisor_role.permissions.append(perm)

        await db.commit()
        await db.refresh(admin_role)

        # Crear o actualizar superusuario admin
        result = await db.execute(select(User).where(User.username == "admin"))
        existing_admin = result.scalar_one_or_none()
        if not existing_admin:
            admin_user = User(
                username="admin",
                email="admin@turnos.com",
                full_name="Administrador",
                hashed_password=get_password_hash("1234"),
                is_superuser=True,
                role_id=admin_role.id,
            )
            db.add(admin_user)
            await db.commit()
            print("✅ Usuario admin creado: admin / 1234")
        else:
            existing_admin.hashed_password = get_password_hash("1234")
            existing_admin.email = "admin@turnos.com"
            await db.commit()
            print("✅ Contraseña admin actualizada: admin / 1234")

        # ── Categorías profesionales de empleados ──
        from app.models.employee import EmployeeCategory

        INITIAL_CATEGORIES = [
            ("Gestor", "Gestor de turnos"),
            ("Supervisor", "Supervisor de operaciones"),
            ("Conductor", "Conductor de vehículos"),
            ("Jefe de Turno", "Jefe de turno operativo"),
            ("Ayudante de Mesa", "Ayudante de mesa de operaciones"),
            ("Agente", "Agente operativo"),
            ("SIC", "Servicio de Información y Comunicación"),
        ]

        for cat_name, cat_desc in INITIAL_CATEGORIES:
            result = await db.execute(
                select(EmployeeCategory).where(EmployeeCategory.name == cat_name)
            )
            if not result.scalar_one_or_none():
                db.add(EmployeeCategory(name=cat_name, description=cat_desc))

        await db.commit()
        print("✅ Categorías profesionales verificadas")

        # ── Tipos de Agente ──
        from app.models.employee import AgentType

        INITIAL_AGENT_TYPES = [
            ("JC-F", "Jornada Completa - Fijo"),
            ("JC-FD", "Jornada Completa - Fin de semana"),
            ("MJ-F", "Media Jornada - Fijo"),
            ("MJ-FD", "Media Jornada - Fin de semana"),
            ("VEC", "Vecinal"),
            ("SUS", "Suplente"),
        ]

        for at_name, at_desc in INITIAL_AGENT_TYPES:
            result = await db.execute(
                select(AgentType).where(AgentType.name == at_name)
            )
            if not result.scalar_one_or_none():
                db.add(AgentType(name=at_name, description=at_desc))

        await db.commit()
        print("✅ Tipos de agente verificados")


app = FastAPI(
    title=settings.APP_NAME,
    description="Sistema de Gestión de Turnos",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def vercel_oidc_token_middleware(request, call_next):
    token_ref = set_vercel_oidc_token(request.headers.get("x-vercel-oidc-token"))
    try:
        return await call_next(request)
    finally:
        reset_vercel_oidc_token(token_ref)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, limitar a dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(roles.router, prefix="/api/v1")
app.include_router(permissions.router, prefix="/api/v1")
app.include_router(employees.router, prefix="/api/v1")
app.include_router(shifts.router, prefix="/api/v1")
app.include_router(assignments.router, prefix="/api/v1")
app.include_router(business_rules.router, prefix="/api/v1")
app.include_router(imports.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")


@app.get("/api/v1/system/setup-db")
async def setup_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await seed_initial_data()
        return {"status": "success", "message": "Base de datos inicializada. Usa admin / 1234"}
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "detail": traceback.format_exc()}


@app.get("/api/v1/system/db-ping")
async def db_ping():
    """Diagnóstico: prueba la conexión a la base de datos y muestra el error exacto."""
    from sqlalchemy import text
    try:
        url_usada = settings.ASYNC_DATABASE_URL
        # Ocultar credenciales para el log
        url_log = url_usada.split("@")[-1] if "@" in url_usada else url_usada
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
        return {
            "status": "ok",
            "db_version": version,
            "host": url_log,
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": str(e),
            "type": type(e).__name__,
            "detail": traceback.format_exc(),
        }


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "docs": "/docs",
        "status": "ok",
        "diagnostico": "/api/v1/system/db-ping",
        "setup": "/api/v1/system/setup-db",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
