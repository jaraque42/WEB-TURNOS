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
        # Si usamos la integración de Vercel con AWS Aurora (IAM Authentication)
        if not self.DATABASE_URL and os.environ.get("PGHOST"):
            db_host = os.environ.get("PGHOST")
            db_port = int(os.environ.get("PGPORT", 5432))
            db_user = os.environ.get("PGUSER")
            db_name = os.environ.get("PGDATABASE", "postgres")
            
            # Generar token si estamos en Vercel con OIDC
            if os.environ.get("VERCEL_OIDC_TOKEN"):
                try:
                    import boto3
                    aws_region = os.environ.get("AWS_REGION", "us-east-1")
                    role_arn = os.environ.get("AWS_ROLE_ARN")
                    oidc_token = os.environ.get("VERCEL_OIDC_TOKEN")
                    
                    sts_client = boto3.client('sts', region_name=aws_region)
                    response = sts_client.assume_role_with_web_identity(
                        RoleArn=role_arn,
                        RoleSessionName="VercelPostgresSession",
                        WebIdentityToken=oidc_token
                    )
                    creds = response['Credentials']
                    
                    rds_client = boto3.client(
                        'rds',
                        region_name=aws_region,
                        aws_access_key_id=creds['AccessKeyId'],
                        aws_secret_access_key=creds['SecretAccessKey'],
                        aws_session_token=creds['SessionToken']
                    )
                    
                    auth_token = rds_client.generate_db_auth_token(
                        DBHostname=db_host,
                        Port=db_port,
                        DBUsername=db_user,
                        Region=aws_region
                    )
                    encoded_token = urllib.parse.quote_plus(auth_token)
                    return f"postgresql+asyncpg://{db_user}:{encoded_token}@{db_host}:{db_port}/{db_name}?ssl=require"
                except Exception as e:
                    print(f"⚠️ Error generando token AWS IAM: {e}")
            
            # Fallback si no pudimos generar token
            return f"postgresql+asyncpg://{db_user}@{db_host}:{db_port}/{db_name}?ssl=require"

        url = self.DATABASE_URL
        if url:
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://") and "+asyncpg" not in url:
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            # asyncpg no acepta ?sslmode=require, necesita ?ssl=require
            url = url.replace("?sslmode=require", "?ssl=require")
            url = url.replace("&sslmode=require", "&ssl=require")
            return url
            
        raise ValueError("DATABASE_URL no está configurada")

    model_config = {
        "env_file": ".env",
        "extra": "ignore",  # Ignorar variables de entorno desconocidas
    }


settings = Settings()
