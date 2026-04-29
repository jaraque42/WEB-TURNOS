import os
import urllib.parse
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "GestionTurnos"
    APP_ENV: str = "development"

    DATABASE_URL: str | None = None

    SECRET_KEY: str = "change_me_in_production_1234567890"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    AGENT_START_COMMAND: str = ""
    AGENT_WORKDIR: str = "/app"
    AGENT_PID_FILE: str = "/tmp/turnos_agent.pid"

    @property
    def USE_AWS_IAM_AUTH(self) -> bool:
        return bool(
            os.environ.get("PGHOST")
            and os.environ.get("AWS_ROLE_ARN")
            and not os.environ.get("PGPASSWORD")
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        # 1. Si Vercel AWS Integration configuró PGHOST, armamos la URL directamente.
        # Si no hay contraseña pero sí OIDC/AWS Role, database.py usará IAM Auth.
        if os.environ.get("PGHOST"):
            db_host = os.environ.get("PGHOST")
            db_port = os.environ.get("PGPORT", "5432")
            db_user = os.environ.get("PGUSER", "postgres")
            db_name = os.environ.get("PGDATABASE", "postgres")
            db_pass = os.environ.get("PGPASSWORD", "")
            
            if db_pass:
                # Si hay contraseña, la incluimos
                return f"postgresql+asyncpg://{db_user}:{urllib.parse.quote_plus(db_pass)}@{db_host}:{db_port}/{db_name}?ssl=require"
            else:
                return f"postgresql+asyncpg://{db_user}@{db_host}:{db_port}/{db_name}?ssl=require"

        # 2. Si no hay PGHOST, intentamos usar DATABASE_URL
        url = self.DATABASE_URL
        if url and "://" in url:
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://") and "+asyncpg" not in url:
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            url = url.replace("?sslmode=require", "?ssl=require")
            url = url.replace("&sslmode=require", "&ssl=require")
            return url
            
        # 3. Fallback genérico para que no crashee al arrancar (crasheará al intentar conectar)
        return "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

    model_config = {
        "env_file": ".env",
        "extra": "ignore",  # Ignorar variables de entorno desconocidas
    }


settings = Settings()
