from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "GestionTurnos"
    APP_ENV: str = "development"

    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    AGENT_START_COMMAND: str = ""
    AGENT_WORKDIR: str = "/app"
    AGENT_PID_FILE: str = "/tmp/turnos_agent.pid"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        # asyncpg no acepta ?sslmode=require, necesita ?ssl=require
        url = url.replace("?sslmode=require", "?ssl=require")
        url = url.replace("&sslmode=require", "&ssl=require")
        return url

    model_config = {
        "env_file": ".env",
        "extra": "ignore",  # Ignorar variables de entorno desconocidas (ej: POSTGRES_USER de Docker)
    }


settings = Settings()
