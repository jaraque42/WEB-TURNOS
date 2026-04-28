/* ─── Auth ────────────────────────────────────────────────── */
export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: string;
  username: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  role_id: string;
  role?: Role;
}

/* ─── Roles & Permissions ─────────────────────────────────── */
export interface Role {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  permissions?: Permission[];
}

export interface Permission {
  id: string;
  name: string;
  description: string | null;
}

/* ─── Employees ───────────────────────────────────────────── */
export interface EmployeeCategory {
  id: string;
  name: string;
  description: string | null;
  weekly_hours?: number;
  is_active: boolean;
}

export interface AgentType {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
}

export interface License {
  id: string;
  employee_id: string;
  license_type: string;
  start_date: string;
  end_date: string;
  status: string;
  reason: string | null;
}

export type EmployeeStatus = 'activo' | 'inactivo' | 'licencia' | 'suspendido';

export interface Employee {
  id: string;
  employee_number: number;
  first_name: string;
  last_name: string;
  email: string | null;
  document_number: string;
  phone: string | null;
  address: string | null;
  location: string | null;
  hire_date: string;
  status: EmployeeStatus;
  category_id: string | null;
  agent_type_id: string | null;
  user_id: string | null;
  category?: EmployeeCategory;
  agent_type?: AgentType;
  licenses?: License[];
  created_at: string;
  updated_at: string;
}

/* ─── Shifts ──────────────────────────────────────────────── */
export interface ShiftType {
  id: string;
  code: string;
  name: string;
  start_time: string;
  end_time: string;
  duration_hours: number;
  color: string;
  is_active: boolean;
}

export interface CoverageRequirement {
  id: string;
  shift_type_id: string;
  day_of_week: number;
  min_employees: number;
  max_employees: number | null;
  employee_category_id: string | null;
  shift_type?: ShiftType;
}

/* ─── Assignments ─────────────────────────────────────────── */
export interface ShiftAssignment {
  id: string;
  employee_id: string;
  shift_type_id: string;
  date: string;
  status: string;
  notes: string | null;
  location: string | null;
  employee_name?: string;
  shift_type_name?: string;
  shift_type_code?: string;
}

export interface SwapRequest {
  id: string;
  requester_assignment_id: string;
  target_assignment_id: string;
  reason: string | null;
  status: string;
  resolved_at: string | null;
}

export interface AssignmentStats {
  total: number;
  by_status: Record<string, number>;
  by_shift_type: Record<string, number>;
  employees_assigned: number;
}

/* ─── Business Rules ──────────────────────────────────────── */
export interface BusinessRule {
  id: string;
  name: string;
  description: string | null;
  category: string;
  is_active: boolean;
  max_value: number;
  employee_category_id: string | null;
}

export interface ShiftIncompatibility {
  id: string;
  shift_type_a_id: string;
  shift_type_b_id: string;
  direction: string;
}

/* ─── API helpers ─────────────────────────────────────────── */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

export interface ValidationError {
  detail: string | Array<{ loc: string[]; msg: string; type: string }>;
}
