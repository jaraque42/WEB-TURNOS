import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { getApiErrorMessage } from '../lib/error';
import type { CurrentUser, Role } from '../types';
import { Plus, Pencil, Trash2, X, KeyRound, Upload } from 'lucide-react';

export default function UsersPage() {
  const qc = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [editing, setEditing] = useState<CurrentUser | null>(null);
  const [resetTarget, setResetTarget] = useState<CurrentUser | null>(null);

  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => api.get<CurrentUser[]>('/users/').then((r) => r.data),
  });

  const { data: roles } = useQuery({
    queryKey: ['roles'],
    queryFn: () => api.get<Role[]>('/roles/').then((r) => r.data),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/users/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  });

  const openCreate = () => { setEditing(null); setShowModal(true); };
  const openEdit = (u: CurrentUser) => { setEditing(u); setShowModal(true); };

  return (
    <>
      <div className="header">
        <h1 className="header-title">Usuarios</h1>
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={() => setShowBulkModal(true)}>
            <Upload size={16} /> Importar masivo
          </button>
          <button className="btn btn-primary" onClick={openCreate}>
            <Plus size={16} /> Nuevo usuario
          </button>
        </div>
      </div>
      <div className="page-content">
        <div className="card">
          {isLoading ? (
            <div className="loading-page"><span className="spinner" /></div>
          ) : users && users.length > 0 ? (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Usuario</th>
                    <th>Nombre completo</th>
                    <th>Email</th>
                    <th>Rol</th>
                    <th>Superusuario</th>
                    <th>Estado</th>
                    <th style={{ width: 130 }}>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td><strong>{u.username}</strong></td>
                      <td>{u.full_name}</td>
                      <td>{u.email}</td>
                      <td>
                        {u.role ? (
                          <span className="badge badge-blue">{u.role.name}</span>
                        ) : (
                          <span className="badge badge-gray">Sin rol</span>
                        )}
                      </td>
                      <td>
                        {u.is_superuser ? (
                          <span className="badge badge-yellow">Sí</span>
                        ) : (
                          <span className="badge badge-gray">No</span>
                        )}
                      </td>
                      <td>
                        <span className={`badge ${u.is_active ? 'badge-green' : 'badge-red'}`}>
                          {u.is_active ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.25rem' }}>
                          <button className="btn btn-icon btn-secondary btn-sm" onClick={() => openEdit(u)} title="Editar">
                            <Pencil size={14} />
                          </button>
                          <button className="btn btn-icon btn-secondary btn-sm" onClick={() => setResetTarget(u)} title="Resetear contraseña">
                            <KeyRound size={14} />
                          </button>
                          <button
                            className="btn btn-icon btn-danger btn-sm"
                            title="Eliminar"
                            onClick={() => { if (confirm(`¿Eliminar usuario "${u.username}"?`)) deleteMut.mutate(u.id); }}
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
            <div className="empty-state">No hay usuarios registrados</div>
          )}
        </div>
      </div>

      {showModal && (
        <UserModal
          user={editing}
          roles={roles ?? []}
          onClose={() => setShowModal(false)}
        />
      )}

      {resetTarget && (
        <ResetPasswordModal
          user={resetTarget}
          onClose={() => setResetTarget(null)}
        />
      )}

      {showBulkModal && (
        <BulkImportModal
          roles={roles ?? []}
          onClose={() => setShowBulkModal(false)}
        />
      )}
    </>
  );
}

/* ─── User Modal (Create / Edit) ──────────────────────────── */
function UserModal({
  user,
  roles,
  onClose,
}: {
  user: CurrentUser | null;
  roles: Role[];
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const isEdit = !!user;

  const [form, setForm] = useState({
    username: user?.username ?? '',
    full_name: user?.full_name ?? '',
    email: user?.email ?? '',
    password: '',
    role_id: user?.role_id ?? (roles[0]?.id ?? ''),
    is_superuser: user?.is_superuser ?? false,
    is_active: user?.is_active ?? true,
  });

  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      isEdit
        ? api.patch(`/users/${user!.id}`, data)
        : api.post('/users/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] });
      onClose();
    },
    onError: (error: unknown) => setError(getApiErrorMessage(error, 'Error al guardar')),
  });

  const submit = () => {
    if (isEdit) {
      // Solo enviar campos modificados
      const payload: Record<string, unknown> = {};
      if (form.full_name !== user!.full_name) payload.full_name = form.full_name;
      if (form.email !== user!.email) payload.email = form.email;
      if (form.role_id !== user!.role_id) payload.role_id = form.role_id;
      if (form.is_active !== user!.is_active) payload.is_active = form.is_active;
      if (form.password) payload.password = form.password;
      mutation.mutate(payload);
    } else {
      if (!form.password) {
        setError('La contraseña es obligatoria');
        return;
      }
      mutation.mutate({
        ...form,
        role_id: form.role_id || null,
      });
    }
  };

  const handleChange = (field: string, value: string | boolean) =>
    setForm((f) => ({ ...f, [field]: value }));

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">{isEdit ? 'Editar usuario' : 'Nuevo usuario'}</h2>
          <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
        </div>

        {error && <div className="error-msg">{error}</div>}

        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Usuario</label>
            <input
              className="form-input"
              value={form.username}
              onChange={(e) => handleChange('username', e.target.value)}
              disabled={isEdit}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Nombre completo</label>
            <input className="form-input" value={form.full_name} onChange={(e) => handleChange('full_name', e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input className="form-input" type="email" value={form.email} onChange={(e) => handleChange('email', e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">{isEdit ? 'Nueva contraseña (dejar vacío = no cambiar)' : 'Contraseña'}</label>
            <input className="form-input" type="password" value={form.password} onChange={(e) => handleChange('password', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Rol</label>
            <select className="form-select" value={form.role_id} onChange={(e) => handleChange('role_id', e.target.value)}>
              <option value="">Sin rol</option>
              {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '1rem', paddingTop: '1.5rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
              <input type="checkbox" checked={form.is_superuser} onChange={(e) => handleChange('is_superuser', e.target.checked)} />
              Superusuario
            </label>
            {isEdit && (
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
                <input type="checkbox" checked={form.is_active} onChange={(e) => handleChange('is_active', e.target.checked)} />
                Activo
              </label>
            )}
          </div>
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

/* ─── Reset Password Modal ────────────────────────────────── */
function ResetPasswordModal({
  user,
  onClose,
}: {
  user: CurrentUser;
  onClose: () => void;
}) {
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const mutation = useMutation({
    mutationFn: (pwd: string) =>
      api.post(`/users/${user.id}/reset-password`, { new_password: pwd }),
    onSuccess: () => setSuccess(true),
    onError: (error: unknown) => setError(getApiErrorMessage(error, 'Error')),
  });

  if (success) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h2 className="modal-title">Contraseña reseteada</h2>
            <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
          </div>
          <p>La contraseña de <strong>{user.username}</strong> fue actualizada correctamente.</p>
          <div className="modal-footer">
            <button className="btn btn-primary" onClick={onClose}>Cerrar</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Resetear contraseña — {user.username}</h2>
          <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
        </div>

        {error && <div className="error-msg">{error}</div>}

        <div className="form-group">
          <label className="form-label">Nueva contraseña</label>
          <input className="form-input" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} autoFocus />
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancelar</button>
          <button className="btn btn-primary" onClick={() => mutation.mutate(newPassword)} disabled={mutation.isPending || !newPassword}>
            {mutation.isPending ? <span className="spinner" /> : 'Resetear'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Bulk Import Modal ────────────────────────────────────── */
function BulkImportModal({
  roles,
  onClose,
}: {
  roles: Role[];
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
      return api.post<{ created: number; failed: number; errors: string[] }>('/users/upload-csv/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    onSuccess: (response) => {
      setResult(response.data);
      qc.invalidateQueries({ queryKey: ['users'] });
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
  type UserFormData = {
    username: string;
    email: string;
    full_name: string;
    password: string;
    role_id: string;
    is_superuser: boolean;
  };

  const [formUsers, setFormUsers] = useState<UserFormData[]>([
    { username: '', email: '', full_name: '', password: '', role_id: roles[0]?.id ?? '', is_superuser: false },
    { username: '', email: '', full_name: '', password: '', role_id: roles[0]?.id ?? '', is_superuser: false },
    { username: '', email: '', full_name: '', password: '', role_id: roles[0]?.id ?? '', is_superuser: false },
  ]);

  const formMutation = useMutation({
    mutationFn: (users: Array<Omit<UserFormData, 'role_id'> & { role_id: string | null }>) =>
      api.post<{ created: number; failed: number; errors: string[] }>('/users/bulk/', users),
    onSuccess: (response) => {
      setResult(response.data);
      qc.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (error: unknown) => setError(getApiErrorMessage(error, 'Error al crear usuarios')),
  });

  const handleFormSubmit = () => {
    const filledUsers = formUsers.filter(u => u.username && u.email && u.full_name && u.password);
    if (filledUsers.length === 0) {
      setError('Completa al menos un usuario');
      return;
    }
    setError('');
    formMutation.mutate(filledUsers.map(u => ({ ...u, role_id: u.role_id || null })));
  };

  const addFormUser = () => {
    setFormUsers([...formUsers, { username: '', email: '', full_name: '', password: '', role_id: roles[0]?.id ?? '', is_superuser: false }]);
  };

  const removeFormUser = (idx: number) => {
    setFormUsers(formUsers.filter((_, i) => i !== idx));
  };

  const updateFormUser = (idx: number, field: keyof UserFormData, value: string | boolean) => {
    const updated = [...formUsers];
    updated[idx] = { ...updated[idx], [field]: value };
    setFormUsers(updated);
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
      <div className="modal modal-lg" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '800px' }}>
        <div className="modal-header">
          <h2 className="modal-title">Importar usuarios masivamente</h2>
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
            Subir archivo
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
              Sube un archivo CSV o Excel (.xlsx) con el siguiente formato:
            </p>
            <pre style={{ background: '#f5f5f5', padding: '1rem', borderRadius: '4px', fontSize: '0.85rem', overflowX: 'auto' }}>
{`username,email,full_name,password,role_name,is_superuser
jperez,jperez@example.com,Juan Pérez,Pass1234,Admin,false
mgarcia,mgarcia@example.com,María García,Pass1234,Operador,false`}
            </pre>

            <div className="form-group" style={{ marginTop: '1.5rem' }}>
              <label className="form-label">Archivo CSV / Excel</label>
              <input
                type="file"
                accept=".csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel"
                className="form-input"
                onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
              />
            </div>
          </div>
        )}

        {/* Form Tab */}
        {tab === 'form' && (
          <div style={{ padding: '1.5rem', maxHeight: '500px', overflowY: 'auto' }}>
            {formUsers.map((user, idx) => (
              <div key={idx} style={{ marginBottom: '1.5rem', padding: '1rem', background: '#f9f9f9', borderRadius: '4px', position: 'relative' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <strong style={{ fontSize: '0.9rem' }}>Usuario #{idx + 1}</strong>
                  {formUsers.length > 1 && (
                    <button className="btn btn-icon btn-danger btn-sm" onClick={() => removeFormUser(idx)} title="Eliminar">
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>

                <div className="form-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
                  <div className="form-group">
                    <label className="form-label">Usuario</label>
                    <input
                      className="form-input"
                      value={user.username}
                      onChange={(e) => updateFormUser(idx, 'username', e.target.value)}
                      placeholder="usuario123"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Email</label>
                    <input
                      type="email"
                      className="form-input"
                      value={user.email}
                      onChange={(e) => updateFormUser(idx, 'email', e.target.value)}
                      placeholder="email@example.com"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Nombre completo</label>
                    <input
                      className="form-input"
                      value={user.full_name}
                      onChange={(e) => updateFormUser(idx, 'full_name', e.target.value)}
                      placeholder="Nombre Apellido"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Contraseña</label>
                    <input
                      type="password"
                      className="form-input"
                      value={user.password}
                      onChange={(e) => updateFormUser(idx, 'password', e.target.value)}
                      placeholder="••••••••"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Rol</label>
                    <select
                      className="form-select"
                      value={user.role_id}
                      onChange={(e) => updateFormUser(idx, 'role_id', e.target.value)}
                    >
                      <option value="">Sin rol</option>
                      {roles.map((r) => (
                        <option key={r.id} value={r.id}>{r.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group" style={{ display: 'flex', alignItems: 'center', paddingTop: '1.5rem' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={user.is_superuser}
                        onChange={(e) => updateFormUser(idx, 'is_superuser', e.target.checked)}
                      />
                      Superusuario
                    </label>
                  </div>
                </div>
              </div>
            ))}

            <button className="btn btn-secondary" onClick={addFormUser} style={{ width: '100%' }}>
              <Plus size={16} /> Agregar usuario
            </button>
          </div>
        )}

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancelar</button>
          {tab === 'csv' ? (
            <button className="btn btn-primary" onClick={handleCsvSubmit} disabled={csvMutation.isPending || !csvFile}>
              {csvMutation.isPending ? <span className="spinner" /> : 'Importar archivo'}
            </button>
          ) : (
            <button className="btn btn-primary" onClick={handleFormSubmit} disabled={formMutation.isPending}>
              {formMutation.isPending ? <span className="spinner" /> : 'Crear usuarios'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
