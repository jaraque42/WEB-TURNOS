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

    class Config:
        env_file = ".env"


settings = Settings()
