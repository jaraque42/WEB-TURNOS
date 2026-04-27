from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.business_rule import RuleCategory, IncompatibilityDirection


# ─── Regla de Negocio ──────────────────────────────────

class BusinessRuleBase(BaseModel):
    name: str = Field(..., max_length=150)
    description: Optional[str] = None
    category: RuleCategory
    max_value: int = Field(..., ge=1)
    employee_category_id: Optional[UUID] = None


class BusinessRuleCreate(BusinessRuleBase):
    pass


class BusinessRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = None
    category: Optional[RuleCategory] = None
    max_value: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None
    employee_category_id: Optional[UUID] = None


class BusinessRuleOut(BusinessRuleBase):
    id: UUID
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Incompatibilidad de Turnos ────────────────────────

class ShiftIncompatibilityBase(BaseModel):
    shift_type_a_id: UUID
    shift_type_b_id: UUID
    direction: IncompatibilityDirection = IncompatibilityDirection.FORWARD
    description: Optional[str] = None


class ShiftIncompatibilityCreate(ShiftIncompatibilityBase):
    pass


class ShiftIncompatibilityUpdate(BaseModel):
    direction: Optional[IncompatibilityDirection] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ShiftIncompatibilityOut(ShiftIncompatibilityBase):
    id: UUID
    is_active: bool
    created_at: datetime

    # Nombres expandidos
    shift_type_a_name: Optional[str] = None
    shift_type_b_name: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Validación previa de asignación ───────────────────

class RuleViolation(BaseModel):
    """Detalle de una violación de regla de negocio."""
    rule_name: str
    category: str
    detail: str
    severity: str = "error"   # "error" o "warning"


class AssignmentValidationRequest(BaseModel):
    """Solicitud para validar una asignación antes de crearla."""
    employee_id: UUID
    shift_type_id: UUID
    date: str  # YYYY-MM-DD


class AssignmentValidationResult(BaseModel):
    """Resultado de la validación de una asignación."""
    is_valid: bool
    violations: List[RuleViolation] = []
    warnings: List[RuleViolation] = []
