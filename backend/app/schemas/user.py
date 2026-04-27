from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.schemas.role import RoleOut


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    password: str
    role_id: Optional[UUID] = None
    is_superuser: bool = False


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class ChangePassword(BaseModel):
    current_password: str
    new_password: str


class UserOut(UserBase):
    id: UUID
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    role: Optional[RoleOut] = None

    model_config = {"from_attributes": True}


# Para el token de autenticación
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class UserBulkCreate(BaseModel):
    """Para crear múltiples usuarios de una vez."""
    users: list[UserCreate]


class UserBulkResult(BaseModel):
    """Resultado de la creación masiva."""
    created: int
    failed: int
    errors: list[str] = []
