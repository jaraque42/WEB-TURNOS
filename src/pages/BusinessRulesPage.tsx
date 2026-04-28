import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { getApiErrorMessage } from '../lib/error';
import type { BusinessRule, ShiftIncompatibility, ShiftType, EmployeeCategory, AgentType } from '../types';
import { Plus, Pencil, Trash2, X, ShieldCheck, AlertTriangle } from 'lucide-react';
import { useAuth } from '../context/useAuth';

export default function BusinessRulesPage() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const [showRuleModal, setShowRuleModal] = useState(false);
  const [editingRule, setEditingRule] = useState<BusinessRule | null>(null);
  const [showIncomModal, setShowIncomModal] = useState(false);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [editingCategory, setEditingCategory] = useState<EmployeeCategory | null>(null);
  const [showAgentTypeModal, setShowAgentTypeModal] = useState(false);
  const [editingAgentType, setEditingAgentType] = useState<AgentType | null>(null);

  const { data: rules, isLoading } = useQuery({
    queryKey: ['business-rules'],
    queryFn: () => api.get<BusinessRule[]>('/business-rules/').then((r) => r.data),
  });

  const { data: incompatibilities } = useQuery({
    queryKey: ['shift-incompatibilities'],
    queryFn: () => api.get<ShiftIncompatibility[]>('/shift-incompatibilities/').then((r) => r.data),
  });

  const { data: shiftTypes } = useQuery({
    queryKey: ['shift-types'],
    queryFn: () => api.get<ShiftType[]>('/shift-types/').then((r) => r.data),
  });

  const { data: categories } = useQuery({
    queryKey: ['employee-categories'],
    queryFn: () => api.get<EmployeeCategory[]>('/employee-categories/').then((r) => r.data),
  });
  const { data: agentTypes } = useQuery({
    queryKey: ['agent-types'],
    queryFn: () => api.get<AgentType[]>('/agent-types/').then((r) => r.data),
  });

  const createCategoryMut = useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      api.post('/employee-categories/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['employee-categories'] });
      setShowCategoryModal(false);
    },
    onError: (err: unknown) => {
      alert(getApiErrorMessage(err, 'Error al crear categoría'));
    },
  });

  const updateCategoryMut = useMutation({
    mutationFn: ({id,data}: {id:string;data:{name:string;description?:string}}) =>
      api.patch(`/employee-categories/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['employee-categories'] });
      setShowCategoryModal(false);
      setEditingCategory(null);
    },
    onError: (err: unknown) => {
      alert(getApiErrorMessage(err, 'Error al actualizar categoría'));
    },
  });

  const deleteCategoryMut = useMutation({
    mutationFn: (id: string) => api.delete(`/employee-categories/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['employee-categories'] }),
    onError: (err: unknown) => {
      alert(getApiErrorMessage(err, 'Error al eliminar categoría'));
    },
  });
  const createAgentTypeMut = useMutation({
    mutationFn: (data: { name: string; description?: string }) => api.post('/agent-types/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agent-types'] });
      setShowAgentTypeModal(false);
    },
    onError: (err: unknown) => {
      alert(getApiErrorMessage(err, 'Error al crear tipo de agente'));
    },
  });
  const updateAgentTypeMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { name: string; description?: string; is_active?: boolean } }) =>
      api.patch(`/agent-types/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agent-types'] });
      setShowAgentTypeModal(false);
      setEditingAgentType(null);
    },
    onError: (err: unknown) => {
      alert(getApiErrorMessage(err, 'Error al actualizar tipo de agente'));
    },
  });
  const deleteAgentTypeMut = useMutation({
    mutationFn: (id: string) => api.delete(`/agent-types/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agent-types'] }),
    onError: (err: unknown) => {
      alert(getApiErrorMessage(err, 'Error al eliminar tipo de agente'));
    },
  });

  const deleteRule = useMutation({
    mutationFn: (id: string) => api.delete(`/business-rules/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['business-rules'] }),
  });

  const deleteIncom = useMutation({
    mutationFn: (id: string) => api.delete(`/shift-incompatibilities/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['shift-incompatibilities'] }),
  });

  // category creation handled by modal

  const shiftMap = Object.fromEntries((shiftTypes ?? []).map((s) => [s.id, s]));
  const permissionNames = new Set((user?.role?.permissions ?? []).map((p) => p.name));
  const canCreateAgentType = Boolean(user?.is_superuser || permissionNames.has('employees:create'));
  const canUpdateAgentType = Boolean(user?.is_superuser || permissionNames.has('employees:update'));
  const canDeleteAgentType = Boolean(user?.is_superuser || permissionNames.has('employees:delete'));

  return (
    <>
      <div className="header">
        <h1 className="header-title">Reglas de Negocio</h1>
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={() => setShowIncomModal(true)}>
            <AlertTriangle size={16} /> Incompatibilidad
          </button>
          <button className="btn btn-secondary" onClick={() => { setEditingCategory(null); setShowCategoryModal(true); }}>
            <Plus size={16} /> Categoría
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => { setEditingAgentType(null); setShowAgentTypeModal(true); }}
            disabled={!canCreateAgentType}
            title={!canCreateAgentType ? 'Sin permiso para crear tipos de agente' : undefined}
          >
            <Plus size={16} /> Tipo de agente
          </button>
          <button className="btn btn-primary" onClick={() => { setEditingRule(null); setShowRuleModal(true); }}>
            <Plus size={16} /> Nueva regla
          </button>
        </div>
      </div>
      <div className="page-content">
        {/* Categories */}
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div className="card-header">
            <h2 className="card-title">Categorías de empleado</h2>
          </div>
          {categories && categories.length > 0 ? (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Nombre</th>
                    <th>Descripción</th>
                    <th>Estado</th>
                    <th style={{ width: 100 }}>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {categories.map((c) => (
                    <tr key={c.id}>
                      <td><strong>{c.name}</strong></td>
                      <td>{c.description ?? '—'}</td>
                      <td>
                        <span className={`badge ${c.is_active ? 'badge-green' : 'badge-red'}`}>
                          {c.is_active ? 'Activa' : 'Inactiva'}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.25rem' }}>
                          <button className="btn btn-icon btn-secondary btn-sm" onClick={() => { setEditingCategory(c); setShowCategoryModal(true); }}>
                            <Pencil size={14} />
                          </button>
                          <button
                            className="btn btn-icon btn-danger btn-sm"
                            onClick={() => { if (confirm('¿Eliminar categoría?')) deleteCategoryMut.mutate(c.id); }}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">No hay categorías</div>
          )}
        </div>

        {/* Agent types */}
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div className="card-header">
            <h2 className="card-title">Tipos de agente</h2>
          </div>
          {agentTypes && agentTypes.length > 0 ? (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Nombre</th>
                    <th>Descripción</th>
                    <th>Estado</th>
                    <th style={{ width: 100 }}>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {agentTypes.map((a) => (
                    <tr key={a.id}>
                      <td><strong>{a.name}</strong></td>
                      <td>{a.description ?? '—'}</td>
                      <td>
                        <span className={`badge ${a.is_active ? 'badge-green' : 'badge-red'}`}>
                          {a.is_active ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.25rem' }}>
                          <button
                            className="btn btn-icon btn-secondary btn-sm"
                            onClick={() => { setEditingAgentType(a); setShowAgentTypeModal(true); }}
                            disabled={!canUpdateAgentType}
                            title={!canUpdateAgentType ? 'Sin permiso para editar tipos de agente' : undefined}
                          >
                            <Pencil size={14} />
                          </button>
                          <button
                            className="btn btn-icon btn-danger btn-sm"
                            onClick={() => { if (confirm('¿Eliminar tipo de agente?')) deleteAgentTypeMut.mutate(a.id); }}
                            disabled={!canDeleteAgentType}
                            title={!canDeleteAgentType ? 'Sin permiso para eliminar tipos de agente' : undefined}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">No hay tipos de agente</div>
          )}
        </div>

        {/* Rules */}
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div className="card-header">
            <h2 className="card-title"><ShieldCheck size={18} style={{ verticalAlign: 'middle', marginRight: 6 }} />Reglas</h2>
          </div>
          {isLoading ? (
            <div className="loading-page"><span className="spinner" /></div>
          ) : rules && rules.length > 0 ? (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Nombre</th>
                    <th>Categoría</th>
                    <th>Valor máx.</th>
                    <th>Aplica a</th>
                    <th>Estado</th>
                    <th style={{ width: 100 }}>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((r) => (
                    <tr key={r.id}>
                      <td><strong>{r.name}</strong><br /><small style={{ color: 'var(--gray-500)' }}>{r.description}</small></td>
                      <td><span className="badge badge-blue">{r.category}</span></td>
                      <td>{r.max_value}</td>
                      <td>
                        {r.employee_category_id
                          ? categories?.find((c) => c.id === r.employee_category_id)?.name ?? '—'
                          : <span className="badge badge-gray">Todas</span>}
                      </td>
                      <td>
                        <span className={`badge ${r.is_active ? 'badge-green' : 'badge-red'}`}>
                          {r.is_active ? 'Activa' : 'Inactiva'}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.25rem' }}>
                          <button className="btn btn-icon btn-secondary btn-sm" onClick={() => { setEditingRule(r); setShowRuleModal(true); }}>
                            <Pencil size={14} />
                          </button>
                          <button
                            className="btn btn-icon btn-danger btn-sm"
                            onClick={() => { if (confirm('¿Eliminar?')) deleteRule.mutate(r.id); }}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">No hay reglas configuradas</div>
          )}
        </div>

        {/* Incompatibilities */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title"><AlertTriangle size={18} style={{ verticalAlign: 'middle', marginRight: 6 }} />Incompatibilidades de turnos</h2>
          </div>
          {incompatibilities && incompatibilities.length > 0 ? (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Turno A</th>
                    <th>Dirección</th>
                    <th>Turno B</th>
                    <th style={{ width: 60 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {incompatibilities.map((inc) => (
                    <tr key={inc.id}>
                      <td>{shiftMap[inc.shift_type_a_id]?.name ?? inc.shift_type_a_id}</td>
                      <td><span className="badge badge-yellow">{inc.direction}</span></td>
                      <td>{shiftMap[inc.shift_type_b_id]?.name ?? inc.shift_type_b_id}</td>
                      <td>
                        <button
                          className="btn btn-icon btn-danger btn-sm"
                          onClick={() => { if (confirm('¿Eliminar?')) deleteIncom.mutate(inc.id); }}
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">No hay incompatibilidades configuradas</div>
          )}
        </div>
      </div>

      {showRuleModal && (
        <RuleModal
          rule={editingRule}
          categories={categories ?? []}
          onClose={() => setShowRuleModal(false)}
        />
      )}
      {showIncomModal && (
        <IncompatibilityModal
          shiftTypes={shiftTypes ?? []}
          onClose={() => setShowIncomModal(false)}
        />
      )}
      {showCategoryModal && (
        <CategoryModal
          category={editingCategory}
          onClose={() => { setShowCategoryModal(false); setEditingCategory(null); }}
          onCreate={(data) => editingCategory ? updateCategoryMut.mutate({id: editingCategory.id, data}) : createCategoryMut.mutate(data)}
          isPending={editingCategory ? updateCategoryMut.isPending : createCategoryMut.isPending}
        />
      )}
      {showAgentTypeModal && (canCreateAgentType || (editingAgentType && canUpdateAgentType)) && (
        <AgentTypeModal
          agentType={editingAgentType}
          onClose={() => { setShowAgentTypeModal(false); setEditingAgentType(null); }}
          onCreate={(data) => editingAgentType ? updateAgentTypeMut.mutate({ id: editingAgentType.id, data }) : createAgentTypeMut.mutate(data)}
          isPending={editingAgentType ? updateAgentTypeMut.isPending : createAgentTypeMut.isPending}
        />
      )}
    </>
  );
}

/* ─── Rule Modal ──────────────────────────────────────────── */
// ─── Category Modal ────────────────────────────────────────────
function CategoryModal({
  category,
  onClose,
  onCreate,
  isPending,
}: {
  category?: EmployeeCategory | null;
  onClose: () => void;
  onCreate: (data: { name: string; description?: string }) => void;
  isPending: boolean;
}) {
  const [form, setForm] = useState({
    name: category?.name ?? '',
    description: category?.description ?? '',
  });
  const [error, setError] = useState('');

  const submit = () => {
    if (!form.name.trim()) {
      setError('El nombre es obligatorio');
      return;
    }
    setError('');
    onCreate({ name: form.name.trim(), description: form.description.trim() || undefined });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">{category ? 'Editar categoría' : 'Nueva categoría'}</h2>
          <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
        </div>
        {error && <div className="error-msg">{error}</div>}
        <div className="form-group">
          <label className="form-label">Nombre</label>
          <input
            className="form-input"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          />
        </div>
        <div className="form-group">
          <label className="form-label">Descripción</label>
          <input
            className="form-input"
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          />
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancelar</button>
          <button className="btn btn-primary" onClick={submit} disabled={isPending}>
            {isPending ? <span className="spinner" /> : category ? 'Guardar' : 'Crear'}
          </button>
        </div>
      </div>
    </div>
  );
}

function AgentTypeModal({
  agentType,
  onClose,
  onCreate,
  isPending,
}: {
  agentType?: AgentType | null;
  onClose: () => void;
  onCreate: (data: { name: string; description?: string; is_active?: boolean }) => void;
  isPending: boolean;
}) {
  const [form, setForm] = useState({
    name: agentType?.name ?? '',
    description: agentType?.description ?? '',
    is_active: agentType?.is_active ?? true,
  });
  const [error, setError] = useState('');

  const submit = () => {
    if (!form.name.trim()) {
      setError('El nombre es obligatorio');
      return;
    }
    setError('');
    onCreate({
      name: form.name.trim(),
      description: form.description.trim() || undefined,
      ...(agentType ? { is_active: form.is_active } : {}),
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">{agentType ? 'Editar tipo de agente' : 'Nuevo tipo de agente'}</h2>
          <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
        </div>
        {error && <div className="error-msg">{error}</div>}
        <div className="form-group">
          <label className="form-label">Nombre</label>
          <input
            className="form-input"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          />
        </div>
        <div className="form-group">
          <label className="form-label">Descripción</label>
          <input
            className="form-input"
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          />
        </div>
        {agentType && (
          <label className="form-checkbox">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
            />
            Activo
          </label>
        )}
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancelar</button>
          <button className="btn btn-primary" onClick={submit} disabled={isPending}>
            {isPending ? <span className="spinner" /> : agentType ? 'Guardar' : 'Crear'}
          </button>
        </div>
      </div>
    </div>
  );
}


function RuleModal({
  rule,
  categories,
  onClose,
}: {
  rule: BusinessRule | null;
  categories: EmployeeCategory[];
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const isEdit = !!rule;

  const [form, setForm] = useState({
    name: rule?.name ?? '',
    description: rule?.description ?? '',
    category: rule?.category ?? 'horas',
    max_value: rule?.max_value ?? 48,
    is_active: rule?.is_active ?? true,
    employee_category_id: rule?.employee_category_id ?? '',
  });
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      isEdit ? api.patch(`/business-rules/${rule!.id}`, data) : api.post('/business-rules/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['business-rules'] });
      onClose();
    },
    onError: (error: unknown) => setError(getApiErrorMessage(error, 'Error')),
  });

  const submit = () => {
    const payload = {
      ...form,
      employee_category_id: form.employee_category_id || null,
    };
    mutation.mutate(payload);
  };

  const handleChange = (field: string, value: string | number | boolean) =>
    setForm((f) => ({ ...f, [field]: value }));

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">{isEdit ? 'Editar regla' : 'Nueva regla'}</h2>
          <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
        </div>
        {error && <div className="error-msg">{error}</div>}

        <div className="form-group">
          <label className="form-label">Nombre</label>
          <input className="form-input" value={form.name} onChange={(e) => handleChange('name', e.target.value)} />
        </div>
        <div className="form-group">
          <label className="form-label">Descripción</label>
          <input className="form-input" value={form.description} onChange={(e) => handleChange('description', e.target.value)} />
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Categoría</label>
            <select className="form-select" value={form.category} onChange={(e) => handleChange('category', e.target.value)}>
              <option value="horas">Horas</option>
              <option value="dias_consecutivos">Días consecutivos</option>
              <option value="descanso">Descanso entre turnos</option>
              <option value="descanso_semanal">Descanso semanal</option>
              <option value="incompatibilidad">Incompatibilidad</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Valor máximo</label>
            <input className="form-input" type="number" value={form.max_value} onChange={(e) => handleChange('max_value', Number(e.target.value))} />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Aplica a categoría</label>
          <select className="form-select" value={form.employee_category_id} onChange={(e) => handleChange('employee_category_id', e.target.value)}>
            <option value="">Todas las categorías</option>
            {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancelar</button>
          <button className="btn btn-primary" onClick={submit} disabled={mutation.isPending}>
            {mutation.isPending ? <span className="spinner" /> : isEdit ? 'Guardar' : 'Crear'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Incompatibility modal ───────────────────────────────── */
function IncompatibilityModal({
  shiftTypes,
  onClose,
}: {
  shiftTypes: ShiftType[];
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    shift_type_a_id: shiftTypes[0]?.id ?? '',
    shift_type_b_id: shiftTypes[1]?.id ?? shiftTypes[0]?.id ?? '',
    direction: 'ambos',
  });
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: (data: typeof form) => api.post('/shift-incompatibilities/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shift-incompatibilities'] });
      onClose();
    },
    onError: (error: unknown) => setError(getApiErrorMessage(error, 'Error')),
  });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Nueva incompatibilidad</h2>
          <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
        </div>
        {error && <div className="error-msg">{error}</div>}

        <div className="form-group">
          <label className="form-label">Turno A</label>
          <select className="form-select" value={form.shift_type_a_id} onChange={(e) => setForm((f) => ({ ...f, shift_type_a_id: e.target.value }))}>
            {shiftTypes.map((s) => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Turno B</label>
          <select className="form-select" value={form.shift_type_b_id} onChange={(e) => setForm((f) => ({ ...f, shift_type_b_id: e.target.value }))}>
            {shiftTypes.map((s) => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Dirección</label>
          <select className="form-select" value={form.direction} onChange={(e) => setForm((f) => ({ ...f, direction: e.target.value }))}>
            <option value="siguiente">Siguiente</option>
            <option value="anterior">Anterior</option>
            <option value="ambos">Ambos</option>
          </select>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancelar</button>
          <button className="btn btn-primary" onClick={() => mutation.mutate(form)} disabled={mutation.isPending}>
            {mutation.isPending ? <span className="spinner" /> : 'Crear'}
          </button>
        </div>
      </div>
    </div>
  );
}
