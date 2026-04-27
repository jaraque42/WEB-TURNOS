import os
import shlex
import subprocess
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.models.user import User
from app.services.auth import get_current_superuser

router = APIRouter(tags=["Sistema"])


def _read_pid() -> int | None:
    try:
        with open(settings.AGENT_PID_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        return None


def _is_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


@router.get("/system/agent/status")
async def agent_status(_: User = Depends(get_current_superuser)):
    pid = _read_pid()
    return {
        "running": _is_running(pid),
        "pid": pid,
        "command": settings.AGENT_START_COMMAND or None,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/system/agent/start")
async def start_agent(_: User = Depends(get_current_superuser)):
    if not settings.AGENT_START_COMMAND.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AGENT_START_COMMAND no está configurado en .env",
        )

    existing_pid = _read_pid()
    if _is_running(existing_pid):
        return {
            "started": False,
            "message": "El agente ya está en ejecución",
            "pid": existing_pid,
        }

    try:
        args = shlex.split(settings.AGENT_START_COMMAND)
        proc = subprocess.Popen(
            args,
            cwd=settings.AGENT_WORKDIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        with open(settings.AGENT_PID_FILE, "w", encoding="utf-8") as f:
            f.write(str(proc.pid))
        return {
            "started": True,
            "message": "Agente iniciado",
            "pid": proc.pid,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No se pudo iniciar el agente: {e}",
        )
