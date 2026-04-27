import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { getApiErrorMessage } from '../lib/error';
import { LOCATION_CATALOG, LOCATION_OPTIONS, parseLocationValue, toLocationValue, type LocationTerminal } from '../lib/locations';
import type { Employee, EmployeeCategory, AgentType } from '../types';
import { Plus, Pencil, Trash2, X, CalendarDays, Upload } from 'lucide-react';
import { useAuth } from '../context/useAuth';

const STATUS_LABELS: Record<string, { label: string; badge: string }> = {
  activo: { label: 'Activo', badge: 'badge-green' },
  inactivo: { label: 'Inactivo', badge: 'badge-red' },
  licencia: { label: 'Licencia', badge: 'badge-yellow' },
  suspendido: { label: 'Suspendido', badge: 'badge-red' },
};

export default function EmployeesPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isSuperuser = user?.is_superuser ?? false;
  const [showModal, setShowModal] = useState(false);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [editing, setEditing] = useState<Employee | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [nameFilter, setNameFilter] = useState('');

  const openEmployeeCalendar = (employeeId: string) => {
    navigate(`/assignments?employee_id=${encodeURIComponent(employeeId)}`);
  };

  const { data: employees, isLoading } = useQuery({
    queryKey: ['employees', nameFilter],
    queryFn: () => api.get<Employee[]>('/employees/', {
      params: nameFilter.trim() ? { q: nameFilter.trim() } : {},
    }).then((r) => r.data),
  });

  const { data: categories } = useQuery({
    queryKey: ['employee-categories'],
    queryFn: () => api.get<EmployeeCategory[]>('/employee-categories/').then((r) => r.data),
  });

  const { data: agentTypes } = useQuery({
    queryKey: ['agent-types'],
    queryFn: () => api.get<AgentType[]>('/agent-types/').then((r) => r.data),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/employees/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['employees'] }),
  });

  const bulkDeleteMut = useMutation({
    mutationFn: (ids: string[]) => api.post('/employees/bulk-delete', ids),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['employees'] });
      setSelectedIds(new Set());
    },
    onError: (err: any) => {
      alert(getApiErrorMessage(err, 'Error al eliminar empleados'));
    },
  });

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (!employees) return;
    if (selectedIds.size === employees.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(employees.map((e) => e.id)));
    }
  };

  const handleBulkDelete = () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`¿Eliminar ${selectedIds.size} empleado(s) seleccionado(s)?`)) return;
    bulkDeleteMut.mutate(Array.from(selectedIds));
  };

  const openCreate = () => { setEditing(null); setShowModal(true); };
  const openEdit = (e: Employee) => { setEditing(e); setShowModal(true); };

  return (
    <>
      <div className="header">
        <h1 className="header-title">Empleados</h1>
        <div className="header-actions">
          {isSuperuser && selectedIds.size > 0 && (
            <button
              className="btn btn-danger"
              onClick={handleBulkDelete}
              disabled={bulkDeleteMut.isPending}
            >
              <Trash2 size={16} /> Eliminar ({selectedIds.size})
            </button>
          )}
          <button className="btn btn-secondary" onClick={() => setShowBulkModal(true)}>
            <Upload size={16} /> Importar masivo
          </button>
          <button className="btn btn-primary" onClick={openCreate}>
            <Plus size={16} /> Nuevo empleado
          </button>
        </div>
      </div>
      <div className="page-content">
        <div className="card">
          <div style={{ marginBottom: '0.75rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <input
              type="text"
              className="form-control"
              placeholder="Filtrar por nombre, documento o email..."
              value={nameFilter}
              onChange={(e) => setNameFilter(e.target.value)}
              style={{ maxWidth: 360 }}
            />
            {nameFilter.trim() && (
              <button className="btn btn-secondary btn-sm" onClick={() => setNameFilter('')}>
                Limpiar
              </button>
            )}
          </div>
          {isLoading ? (
            <div className="loading-page"><span className="spinner" /></div>
          ) : employees && employees.length > 0 ? (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    {isSuperuser && (
                      <th style={{ width: 40 }}>
                        <input
                          type="checkbox"
                          checked={employees!.length > 0 && selectedIds.size === employees!.length}
                          onChange={toggleSelectAll}
                        />
                      </th>
                    )}
                    <th>ID</th>
                    <th>Nombre completo</th>
                    <th>Email</th>
                    <th>Documento</th>
                    <th>Categoría</th>
                    <th>Tipo agente</th>
                    <th>Estado</th>
                    <th style={{ width: 140 }}>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {employees.map((e) => {
                    const st = STATUS_LABELS[e.status] ?? { label: e.status, badge: '' };
                    return (
                      <tr key={e.id} style={selectedIds.has(e.id) ? { backgroundColor: 'var(--color-primary-50, #eff6ff)' } : undefined}>
                        {isSuperuser && (
                          <td>
                            <input
                              type="checkbox"
                              checked={selectedIds.has(e.id)}
                              onChange={() => toggleSelect(e.id)}
                            />
                          </td>
                        )}
                        <td>
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '0.15rem 0.5rem', fontSize: '0.8rem' }}
                            onClick={() => openEmployeeCalendar(e.id)}
                            title="Ver calendario del empleado"
                          >
                            <strong>{e.employee_number}</strong>
                          </button>
                        </td>
                        <td>
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '0.15rem 0.5rem', fontSize: '0.8rem' }}
                            onClick={() => openEmployeeCalendar(e.id)}
                            title="Ver calendario del empleado"
                          >
                            {e.last_name}, {e.first_name}
                          </button>
                        </td>
                        <td>{e.email ?? '—'}</td>
                        <td>{e.document_number}</td>
                        <td>{e.category?.name ?? '—'}</td>
                        <td>{e.agent_type?.name ?? '—'}</td>
                        <td>
                          <span className={`badge ${st.badge}`}>{st.label}</span>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.25rem' }}>
                            <button
                              className="btn btn-icon btn-secondary btn-sm"
                              title="Ver calendario"
                              onClick={() => openEmployeeCalendar(e.id)}
                            >
                              <CalendarDays size={14} />
                            </button>
                            <button className="btn btn-icon btn-secondary btn-sm" onClick={() => openEdit(e)}>
                              <Pencil size={14} />
                            </button>
                            <button
                              className="btn btn-icon btn-danger btn-sm"
                              onClick={() => { if (confirm('¿Eliminar?')) deleteMut.mutate(e.id); }}
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">No hay empleados registrados</div>
          )}
        </div>
      </div>

      {showModal && (
        <EmployeeModal
          employee={editing}
          categories={categories ?? []}
          agentTypes={agentTypes ?? []}
          onClose={() => setShowModal(false)}
        />
      )}

      {showBulkModal && (
        <BulkImportModal
          categories={categories ?? []}
          agentTypes={agentTypes ?? []}
          onClose={() => setShowBulkModal(false)}
        />
      )}
    </>
  );
}

/* ─── Modal ───────────────────────────────────────────────── */
function EmployeeModal({
  employee,
  categories,
  agentTypes,
  onClose,
}: {
  employee: Employee | null;
  categories: EmployeeCategory[];
  agentTypes: AgentType[];
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const isEdit = !!employee;

  const [form, setForm] = useState({
    first_name: employee?.first_name ?? '',
    last_name: employee?.last_name ?? '',
    email: employee?.email ?? '',
    document_number: employee?.document_number ?? '',
    phone: employee?.phone ?? '',
    address: employee?.address ?? '',
    hire_date: employee?.hire_date?.slice(0, 10) ?? new Date().toISOString().slice(0, 10),
    category_id: employee?.category_id ?? '',
    agent_type_id: employee?.agent_type_id ?? '',
    status: employee?.status ?? 'activo',
  });
  const parsedLocation = employee?.location ? parseLocationValue(employee.location) : null;
  const [locationTerminal, setLocationTerminal] = useState<LocationTerminal | ''>(parsedLocation?.terminal ?? '');
  const [locationSubcategory, setLocationSubcategory] = useState(parsedLocation?.subcategory ?? '');

  const [error, setError] = useState('');

  const locationValue = locationTerminal && locationSubcategory
    ? toLocationValue(locationTerminal, locationSubcategory)
    : '';
  const locationSubcategories = locationTerminal ? LOCATION_CATALOG[locationTerminal] : [];

  const mutation = useMutation({
    mutationFn: (data: typeof form) => {
      // Enviar solo los campos que el backend espera
      const payload: Record<string, unknown> = { ...data };
      // Convertir strings vacíos en null para campos opcionales
      if (!payload.phone) payload.phone = null;
      if (!payload.address) payload.address = null;
      if (!payload.email) payload.email = null;
      if (!payload.category_id) payload.category_id = null;
      if (!payload.agent_type_id) payload.agent_type_id = null;
      payload.location = locationValue || null;

      return isEdit
        ? api.patch(`/employees/${employee!.id}`, payload)
        : api.post('/employees/', payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['employees'] });
      onClose();
    },
    onError: (error: unknown) => {
      setError(getApiErrorMessage(error, 'Error al guardar'));
    },
  });

  const handleChange = (field: string, value: string | boolean) =>
    setForm((f) => ({ ...f, [field]: value }));

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">{isEdit ? 'Editar empleado' : 'Nuevo empleado'}</h2>
          <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
        </div>

        {error && <div className="error-msg">{error}</div>}

        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Nombre</label>
            <input className="form-input" value={form.first_name} onChange={(e) => handleChange('first_name', e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">Apellido</label>
            <input className="form-input" value={form.last_name} onChange={(e) => handleChange('last_name', e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input className="form-input" type="email" value={form.email} onChange={(e) => handleChange('email', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Documento</label>
            <input className="form-input" value={form.document_number} onChange={(e) => handleChange('document_number', e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">Teléfono</label>
            <input className="form-input" value={form.phone} onChange={(e) => handleChange('phone', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Dirección</label>
            <input className="form-input" value={form.address} onChange={(e) => handleChange('address', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Terminal <span style={{ fontWeight: 400, color: 'var(--gray-400)' }}>(opcional)</span></label>
            <select
              className="form-select"
              value={locationTerminal}
              onChange={(e) => {
                const terminal = e.target.value as LocationTerminal | '';
                setLocationTerminal(terminal);
                setLocationSubcategory('');
              }}
            >
              <option value="">— Sin terminal —</option>
              {Object.keys(LOCATION_CATALOG).map((terminal) => (
                <option key={terminal} value={terminal}>{terminal}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Subcategoría <span style={{ fontWeight: 400, color: 'var(--gray-400)' }}>(opcional)</span></label>
            <select
              className="form-select"
              value={locationSubcategory}
              onChange={(e) => setLocationSubcategory(e.target.value)}
              disabled={!locationTerminal}
            >
              <option value="">— Sin subcategoría —</option>
              {locationSubcategories.map((subcategory) => (
                <option key={subcategory} value={subcategory}>{subcategory}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Fecha ingreso</label>
            <input className="form-input" type="date" value={form.hire_date} onChange={(e) => handleChange('hire_date', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Categoría</label>
            <select className="form-select" value={form.category_id} onChange={(e) => handleChange('category_id', e.target.value)}>
              <option value="">— Sin categoría —</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Tipo de agente</label>
            <select className="form-select" value={form.agent_type_id} onChange={(e) => handleChange('agent_type_id', e.target.value)}>
              <option value="">— Sin tipo —</option>
              {agentTypes.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
          {isEdit && (
            <div className="form-group">
              <label className="form-label">Estado</label>
              <select className="form-select" value={form.status} onChange={(e) => handleChange('status', e.target.value)}>
                <option value="activo">Activo</option>
                <option value="inactivo">Inactivo</option>
                <option value="licencia">Licencia</option>
                <option value="suspendido">Suspendido</option>
              </select>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancelar</button>
          <button className="btn btn-primary" onClick={() => mutation.mutate(form)} disabled={mutation.isPending}>
            {mutation.isPending ? <span className="spinner" /> : isEdit ? 'Guardar' : 'Crear'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Bulk Import Modal ────────────────────────────────────── */
function BulkImportModal({
  categories,
  agentTypes,
  onClose,
}: {
  categories: EmployeeCategory[];
  agentTypes: AgentType[];
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'csv' | 'form'>('csv');
  const [error, setError] = useState('');
  const [result, setResult] = useState<{ created: number; failed: number; errors: string[] } | null>(null);

  // CSV Upload
  const [csvFile, setCsvFile] = useState<File | null>(null);

  const csvMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return api.post<{ created: number; failed: number; errors: string[] }>('/employees/upload-csv/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    onSuccess: (response) => {
      setResult(response.data);
      qc.invalidateQueries({ queryKey: ['employees'] });
    },
    onError: (error: unknown) => setError(getApiErrorMessage(error, 'Error al procesar CSV')),
  });

  const handleCsvSubmit = () => {
    if (!csvFile) {
      setError('Selecciona un archivo CSV');
      return;
    }
    setError('');
    csvMutation.mutate(csvFile);
  };

  // Form-based bulk create
  type EmployeeFormData = {
    first_name: string;
    last_name: string;
    document_number: string;
    email: string;
    phone: string;
    address: string;
    location: string;
    hire_date: string;
    category_id: string;
    agent_type_id: string;
  };

  const [formEmployees, setFormEmployees] = useState<EmployeeFormData[]>([
    { first_name: '', last_name: '', document_number: '', email: '', phone: '', address: '', location: '', hire_date: '', category_id: '', agent_type_id: '' },
    { first_name: '', last_name: '', document_number: '', email: '', phone: '', address: '', location: '', hire_date: '', category_id: '', agent_type_id: '' },
    { first_name: '', last_name: '', document_number: '', email: '', phone: '', address: '', location: '', hire_date: '', category_id: '', agent_type_id: '' },
  ]);

  const formMutation = useMutation({
    mutationFn: (employees: Array<{
      first_name: string;
      last_name: string;
      document_number: string;
      email: string | null;
      phone: string | null;
      address: string | null;
      location: string | null;
      hire_date: string;
      category_id: string | null;
      agent_type_id: string | null;
    }>) =>
      api.post<{ created: number; failed: number; errors: string[] }>('/employees/bulk/', employees),
    onSuccess: (response) => {
      setResult(response.data);
      qc.invalidateQueries({ queryKey: ['employees'] });
    },
    onError: (error: unknown) => setError(getApiErrorMessage(error, 'Error al crear empleados')),
  });

  const handleFormSubmit = () => {
    const filledEmployees = formEmployees.filter(e => e.first_name && e.last_name && e.document_number && e.hire_date);
    if (filledEmployees.length === 0) {
      setError('Completa al menos un empleado');
      return;
    }
    setError('');
    formMutation.mutate(filledEmployees.map(e => ({ 
      ...e, 
      category_id: e.category_id || null,
      agent_type_id: e.agent_type_id || null,
      email: e.email || null,
      phone: e.phone || null,
      address: e.address || null,
      location: e.location || null,
    })));
  };

  const addFormEmployee = () => {
    setFormEmployees([...formEmployees, { first_name: '', last_name: '', document_number: '', email: '', phone: '', address: '', location: '', hire_date: '', category_id: '', agent_type_id: '' }]);
  };

  const removeFormEmployee = (idx: number) => {
    setFormEmployees(formEmployees.filter((_, i) => i !== idx));
  };

  const updateFormEmployee = (idx: number, field: keyof EmployeeFormData, value: string) => {
    const updated = [...formEmployees];
    updated[idx] = { ...updated[idx], [field]: value };
    setFormEmployees(updated);
  };

  if (result) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h2 className="modal-title">Resultado de importación</h2>
            <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
          </div>

          <div style={{ padding: '1rem' }}>
            <p style={{ marginBottom: '1rem' }}>
              <strong style={{ color: 'green' }}>✓ Creados: {result.created}</strong><br />
              <strong style={{ color: result.failed > 0 ? 'red' : 'gray' }}>✗ Fallidos: {result.failed}</strong>
            </p>

            {result.errors.length > 0 && (
              <div style={{ maxHeight: '300px', overflowY: 'auto', background: '#f9f9f9', padding: '1rem', borderRadius: '4px' }}>
                <strong>Errores:</strong>
                <ul style={{ margin: '0.5rem 0 0 0', paddingLeft: '1.5rem' }}>
                  {result.errors.map((err, i) => (
                    <li key={i} style={{ fontSize: '0.9rem', color: '#d32f2f' }}>{err}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button className="btn btn-primary" onClick={onClose}>Cerrar</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-lg" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '900px' }}>
        <div className="modal-header">
          <h2 className="modal-title">Importar empleados masivamente</h2>
          <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
        </div>

        {error && <div className="error-msg">{error}</div>}

        {/* Tabs */}
        <div style={{ display: 'flex', gap: '0.5rem', padding: '0 1.5rem', borderBottom: '1px solid #e0e0e0' }}>
          <button
            onClick={() => setTab('csv')}
            style={{
              padding: '0.75rem 1.5rem',
              background: 'none',
              border: 'none',
              borderBottom: tab === 'csv' ? '2px solid #2563eb' : '2px solid transparent',
              color: tab === 'csv' ? '#2563eb' : '#666',
              fontWeight: tab === 'csv' ? 600 : 400,
              cursor: 'pointer',
            }}
          >
            Subir CSV
          </button>
          <button
            onClick={() => setTab('form')}
            style={{
              padding: '0.75rem 1.5rem',
              background: 'none',
              border: 'none',
              borderBottom: tab === 'form' ? '2px solid #2563eb' : '2px solid transparent',
              color: tab === 'form' ? '#2563eb' : '#666',
              fontWeight: tab === 'form' ? 600 : 400,
              cursor: 'pointer',
            }}
          >
            Formulario múltiple
          </button>
        </div>

        {/* CSV Tab */}
        {tab === 'csv' && (
          <div style={{ padding: '1.5rem' }}>
            <p style={{ marginBottom: '1rem', fontSize: '0.9rem', color: '#666' }}>
              Sube un archivo CSV con el siguiente formato:
            </p>
            <pre style={{ background: '#f5f5f5', padding: '1rem', borderRadius: '4px', fontSize: '0.85rem', overflowX: 'auto' }}>
{`first_name,last_name,document_number,email,phone,address,location,hire_date,category_name,agent_type_name
Juan,Pérez,12345678,jperez@example.com,555-1234,Calle 123,T123:D63,2025-01-15,Full-time,MJ-F
María,García,87654321,mgarcia@example.com,555-5678,Av Principal 456,T4:PISTA,2025-02-01,Part-time,JC-FD`}
            </pre>

            <div className="form-group" style={{ marginTop: '1.5rem' }}>
              <label className="form-label">Archivo CSV</label>
              <input
                type="file"
                accept=".csv"
                className="form-input"
                onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
              />
            </div>
          </div>
        )}

        {/* Form Tab */}
        {tab === 'form' && (
          <div style={{ padding: '1.5rem', maxHeight: '500px', overflowY: 'auto' }}>
            {formEmployees.map((emp, idx) => (
              <div key={idx} style={{ marginBottom: '1.5rem', padding: '1rem', background: '#f9f9f9', borderRadius: '4px', position: 'relative' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <strong style={{ fontSize: '0.9rem' }}>Empleado #{idx + 1}</strong>
                  {formEmployees.length > 1 && (
                    <button className="btn btn-icon btn-danger btn-sm" onClick={() => removeFormEmployee(idx)} title="Eliminar">
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>

                <div className="form-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                  <div className="form-group">
                    <label className="form-label">Nombre</label>
                    <input
                      className="form-input"
                      value={emp.first_name}
                      onChange={(e) => updateFormEmployee(idx, 'first_name', e.target.value)}
                      placeholder="Juan"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Apellido</label>
                    <input
                      className="form-input"
                      value={emp.last_name}
                      onChange={(e) => updateFormEmployee(idx, 'last_name', e.target.value)}
                      placeholder="Pérez"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Documento</label>
                    <input
                      className="form-input"
                      value={emp.document_number}
                      onChange={(e) => updateFormEmployee(idx, 'document_number', e.target.value)}
                      placeholder="12345678"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Email</label>
                    <input
                      type="email"
                      className="form-input"
                      value={emp.email}
                      onChange={(e) => updateFormEmployee(idx, 'email', e.target.value)}
                      placeholder="email@example.com"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Teléfono</label>
                    <input
                      className="form-input"
                      value={emp.phone}
                      onChange={(e) => updateFormEmployee(idx, 'phone', e.target.value)}
                      placeholder="555-1234"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Fecha ingreso</label>
                    <input
                      type="date"
                      className="form-input"
                      value={emp.hire_date}
                      onChange={(e) => updateFormEmployee(idx, 'hire_date', e.target.value)}
                    />
                  </div>
                  <div className="form-group" style={{ gridColumn: 'span 3' }}>
                    <label className="form-label">Dirección</label>
                    <input
                      className="form-input"
                      value={emp.address}
                      onChange={(e) => updateFormEmployee(idx, 'address', e.target.value)}
                      placeholder="Calle 123"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Ubicación</label>
                    <select
                      className="form-select"
                      value={emp.location}
                      onChange={(e) => updateFormEmployee(idx, 'location', e.target.value)}
                    >
                      <option value="">Sin ubicación</option>
                      {LOCATION_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Categoría</label>
                    <select
                      className="form-select"
                      value={emp.category_id}
                      onChange={(e) => updateFormEmployee(idx, 'category_id', e.target.value)}
                    >
                      <option value="">Sin categoría</option>
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Tipo de agente</label>
                    <select
                      className="form-select"
                      value={emp.agent_type_id}
                      onChange={(e) => updateFormEmployee(idx, 'agent_type_id', e.target.value)}
                    >
                      <option value="">Sin tipo</option>
                      {agentTypes.map((t) => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            ))}

            <button className="btn btn-secondary" onClick={addFormEmployee} style={{ width: '100%' }}>
              <Plus size={16} /> Agregar empleado
            </button>
          </div>
        )}

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancelar</button>
          {tab === 'csv' ? (
            <button className="btn btn-primary" onClick={handleCsvSubmit} disabled={csvMutation.isPending || !csvFile}>
              {csvMutation.isPending ? <span className="spinner" /> : 'Importar CSV'}
            </button>
          ) : (
            <button className="btn btn-primary" onClick={handleFormSubmit} disabled={formMutation.isPending}>
              {formMutation.isPending ? <span className="spinner" /> : 'Crear empleados'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
