from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.employee import EmployeeStatus, LicenseType, LicenseStatus


# ─── Categoría de Empleado ──────────────────────────────
class EmployeeCategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None


class EmployeeCategoryCreate(EmployeeCategoryBase):
    pass


class EmployeeCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class EmployeeCategoryOut(EmployeeCategoryBase):
    id: UUID
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Tipo de Agente ─────────────────────────────────────
class AgentTypeBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None


class AgentTypeCreate(AgentTypeBase):
    pass


class AgentTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class AgentTypeOut(AgentTypeBase):
    id: UUID
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Licencia ───────────────────────────────────────────
class LicenseBase(BaseModel):
    license_type: LicenseType
    start_date: date
    end_date: date
    reason: Optional[str] = None


class LicenseCreate(LicenseBase):
    employee_id: UUID


class LicenseUpdate(BaseModel):
    license_type: Optional[LicenseType] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = None
    status: Optional[LicenseStatus] = None


class LicenseOut(LicenseBase):
    id: UUID
    status: LicenseStatus
    employee_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Empleado ───────────────────────────────────────────
class EmployeeCreate(BaseModel):
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    document_number: str = Field(..., max_length=30)
    phone: Optional[str] = Field(None, max_length=30)
    address: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=150)
    hire_date: date
    category_id: Optional[UUID] = None
    agent_type_id: Optional[UUID] = None
    user_id: Optional[UUID] = None


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    document_number: Optional[str] = Field(None, max_length=30)
    phone: Optional[str] = Field(None, max_length=30)
    address: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=150)
    hire_date: Optional[date] = None
    status: Optional[EmployeeStatus] = None
    category_id: Optional[UUID] = None
    agent_type_id: Optional[UUID] = None
    user_id: Optional[UUID] = None


class EmployeeOut(BaseModel):
    id: UUID
    employee_number: int
    first_name: str
    last_name: str
    email: Optional[str] = None
    document_number: str
    phone: Optional[str] = None
    address: Optional[str] = None
    location: Optional[str] = None
    hire_date: date
    status: EmployeeStatus
    category: Optional[EmployeeCategoryOut] = None
    agent_type: Optional[AgentTypeOut] = None
    user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmployeeDetailOut(EmployeeOut):
    """Empleado con sus licencias incluidas."""
    licenses: List[LicenseOut] = []

    model_config = {"from_attributes": True}


# ─── Bulk Operations ────────────────────────────────────
class EmployeeBulkResult(BaseModel):
    """Resultado de la creación masiva de empleados."""
    created: int
    failed: int
    errors: list[str] = []
