import asyncio
import os
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from threading import Lock

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings

_aws_credentials_cache: dict[str, object] = {}
_aws_credentials_lock = Lock()
_vercel_oidc_token: ContextVar[str | None] = ContextVar("vercel_oidc_token", default=None)


def set_vercel_oidc_token(token: str | None):
    return _vercel_oidc_token.set(token)


def reset_vercel_oidc_token(token):
    _vercel_oidc_token.reset(token)


def _get_vercel_oidc_token() -> str:
    token = _vercel_oidc_token.get() or os.environ.get("VERCEL_OIDC_TOKEN")
    if not token:
        raise RuntimeError(
            "Falta el token OIDC de Vercel. En producción debe llegar en "
            "la cabecera x-vercel-oidc-token; en local usa `vercel env pull`."
        )
    return token


def _get_aws_credentials() -> dict[str, str]:
    now = datetime.now(timezone.utc)
    expires_at = _aws_credentials_cache.get("expires_at")
    if isinstance(expires_at, datetime) and expires_at > now + timedelta(minutes=5):
        return _aws_credentials_cache["credentials"]  # type: ignore[return-value]

    with _aws_credentials_lock:
        expires_at = _aws_credentials_cache.get("expires_at")
        if isinstance(expires_at, datetime) and expires_at > now + timedelta(minutes=5):
            return _aws_credentials_cache["credentials"]  # type: ignore[return-value]

        import boto3

        response = boto3.client(
            "sts",
            region_name=os.environ.get("AWS_REGION"),
        ).assume_role_with_web_identity(
            RoleArn=os.environ["AWS_ROLE_ARN"],
            RoleSessionName="vercel-aurora-postgres",
            WebIdentityToken=_get_vercel_oidc_token(),
        )
        credentials = response["Credentials"]
        cached_credentials = {
            "aws_access_key_id": credentials["AccessKeyId"],
            "aws_secret_access_key": credentials["SecretAccessKey"],
            "aws_session_token": credentials["SessionToken"],
        }
        _aws_credentials_cache["credentials"] = cached_credentials
        _aws_credentials_cache["expires_at"] = credentials["Expiration"]
        return cached_credentials


def _generate_iam_auth_token() -> str:
    host = os.environ["PGHOST"]
    port = int(os.environ.get("PGPORT", "5432"))
    user = os.environ.get("PGUSER", "postgres")
    region = os.environ.get("AWS_REGION", "us-east-1")

    import boto3

    rds_client = boto3.client("rds", region_name=region, **_get_aws_credentials())
    return rds_client.generate_db_auth_token(
        DBHostname=host,
        Port=port,
        DBUsername=user,
        Region=region,
    )


async def _create_iam_connection():
    token = await asyncio.to_thread(_generate_iam_auth_token)
    return await asyncpg.connect(
        host=os.environ["PGHOST"],
        port=int(os.environ.get("PGPORT", "5432")),
        user=os.environ.get("PGUSER", "postgres"),
        password=token,
        database=os.environ.get("PGDATABASE", "postgres"),
        ssl="require",
        timeout=float(os.environ.get("PGCONNECT_TIMEOUT", "30")),
    )


if settings.USE_AWS_IAM_AUTH:
    engine = create_async_engine(
        "postgresql+asyncpg://",
        echo=settings.APP_ENV == "development",
        pool_pre_ping=True,
        poolclass=NullPool,
        async_creator=_create_iam_connection,
    )
else:
    engine = create_async_engine(
        settings.ASYNC_DATABASE_URL,
        echo=settings.APP_ENV == "development",
        pool_pre_ping=True,
    )

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
