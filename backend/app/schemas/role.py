from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class PermissionBase(BaseModel):
    name: str
    description: Optional[str] = None


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class PermissionOut(PermissionBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    permission_ids: Optional[List[UUID]] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permission_ids: Optional[List[UUID]] = None


class RoleOut(RoleBase):
    id: UUID
    is_active: bool
    created_at: datetime
    permissions: List[PermissionOut] = []

    model_config = {"from_attributes": True}
