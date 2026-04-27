import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.database import Base, get_db
from app.main import app

# Base de datos en memoria para tests (SQLite async)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Crear y limpiar tablas para cada test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, db: AsyncSession) -> str:
    """Crea un superusuario y devuelve su token JWT."""
    from app.core.security import get_password_hash
    from app.models.user import User
    from app.models.role import Role

    role = Role(name="admin", description="Admin role")
    db.add(role)
    await db.commit()
    await db.refresh(role)

    user = User(
        username="testadmin",
        email="testadmin@test.com",
        full_name="Test Admin",
        hashed_password=get_password_hash("testpass123"),
        is_superuser=True,
        role_id=role.id,
    )
    db.add(user)
    await db.commit()

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "testadmin", "password": "testpass123"},
    )
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def user_token(client: AsyncClient, db: AsyncSession) -> str:
    """Crea un usuario normal y devuelve su token JWT."""
    from app.core.security import get_password_hash
    from app.models.user import User
    from app.models.role import Role

    # Reusar el rol admin si existe, sino crear uno
    from sqlalchemy import select
    result = await db.execute(select(Role).where(Role.name == "operator"))
    role = result.scalar_one_or_none()
    if not role:
        role = Role(name="operator", description="Operator role")
        db.add(role)
        await db.commit()
        await db.refresh(role)

    user = User(
        username="testuser",
        email="testuser@test.com",
        full_name="Test User",
        hashed_password=get_password_hash("testpass123"),
        is_superuser=False,
        role_id=role.id,
    )
    db.add(user)
    await db.commit()

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "testpass123"},
    )
    return response.json()["access_token"]
