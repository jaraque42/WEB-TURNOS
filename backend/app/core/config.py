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
    def ASYNC_DATABASE_URL(self) -> str:
        # 1. Si Vercel AWS Integration configuró PGHOST, armamos la URL directamente.
        # Si el usuario configuró PGPASSWORD en Vercel, lo usamos.
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
                # AWS IAM requiere token, pero en Vercel Serverless el token OIDC viene en el header de cada petición.
                # Como SQLAlchemy se inicializa globalmente, no podemos inyectar el header aquí fácilmente.
                # Si intentamos conectar sin contraseña, fallará en la petición si IAM es obligatorio.
                # Recomendación para el usuario: crear la variable PGPASSWORD en Vercel.
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
