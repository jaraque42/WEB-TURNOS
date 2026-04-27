import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { getApiErrorMessage } from '../lib/error';
import { LOCATION_CATALOG, toLocationValue, type LocationTerminal } from '../lib/locations';
import type { ShiftType, Employee, EmployeeCategory } from '../types';
import { Plus, Pencil, Trash2, X, UserPlus } from 'lucide-react';

const SHIFT_CODE_PATTERN = /^(M|T|N|F)-[A-Z0-9]+-[A-Z0-9]+$/;

export default function ShiftTypesPage() {
  const qc = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<ShiftType | null>(null);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [assigningShiftType, setAssigningShiftType] = useState<ShiftType | null>(null);

  const { data: types, isLoading } = useQuery({
    queryKey: ['shift-types'],
    queryFn: () => api.get<ShiftType[]>('/shift-types/').then((r) => r.data),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/shift-types/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['shift-types'] }),
  });

  return (
    <>
      <div className="header">
        <h1 className="header-title">Tipos de Turno</h1>
        <div className="header-actions">
          <button className="btn btn-primary" onClick={() => { setEditing(null); setShowModal(true); }}>
            <Plus size={16} /> Nuevo tipo
          </button>
        </div>
      </div>
      <div className="page-content">
        <div className="card">
          {isLoading ? (
            <div className="loading-page"><span className="spinner" /></div>
          ) : types && types.length > 0 ? (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Código</th>
                    <th>Nombre</th>
                    <th>Horario</th>
                    <th>Duración</th>
                    <th>Color</th>
                    <th>Estado</th>
                    <th style={{ width: 130 }}>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {types.map((t) => (
                    <tr key={t.id}>
                      <td><strong>{t.code}</strong></td>
                      <td>{t.name}</td>
                      <td>{t.start_time?.slice(0, 5)} – {t.end_time?.slice(0, 5)}</td>
                      <td>{t.duration_hours}h</td>
                      <td>
                        <span
                          style={{
                            display: 'inline-block',
                            width: 24,
                            height: 24,
                            borderRadius: 4,
                            background: t.color,
                            border: '1px solid var(--gray-300)',
                          }}
                        />
                      </td>
                      <td>
                        <span className={`badge ${t.is_active ? 'badge-green' : 'badge-red'}`}>
                          {t.is_active ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.25rem' }}>
                          <button
                            className="btn btn-icon btn-primary btn-sm"
                            onClick={() => { setAssigningShiftType(t); setShowAssignModal(true); }}
                            title="Asignar empleados"
                          >
                            <UserPlus size={14} />
                          </button>
                          <button className="btn btn-icon btn-secondary btn-sm" onClick={() => { setEditing(t); setShowModal(true); }}>
                            <Pencil size={14} />
                          </button>
                          <button
                            className="btn btn-icon btn-danger btn-sm"
                            onClick={() => { if (confirm('¿Eliminar?')) deleteMut.mutate(t.id); }}
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
            <div className="empty-state">No hay tipos de turno registrados</div>
          )}
        </div>
      </div>

      {showModal && (
        <ShiftTypeModal
          shiftType={editing}
          onClose={() => setShowModal(false)}
        />
      )}

      {showAssignModal && assigningShiftType && (
        <AssignEmployeesModal
          shiftType={assigningShiftType}
          onClose={() => { setShowAssignModal(false); setAssigningShiftType(null); }}
        />
      )}
    </>
  );
}

/* ─── Modal ───────────────────────────────────────────────── */
function ShiftTypeModal({ shiftType, onClose }: { shiftType: ShiftType | null; onClose: () => void }) {
  const qc = useQueryClient();
  const isEdit = !!shiftType;

  const [form, setForm] = useState({
    code: shiftType?.code ?? '',
    name: shiftType?.name ?? '',
    start_time: shiftType?.start_time?.slice(0, 5) ?? '08:00',
    end_time: shiftType?.end_time?.slice(0, 5) ?? '16:00',
    duration_hours: shiftType?.duration_hours ?? 8,
    color: shiftType?.color ?? '#2563eb',
    is_active: shiftType?.is_active ?? true,
  });
  const [locationTerminal, setLocationTerminal] = useState<LocationTerminal | ''>('');
  const [locationSubcategory, setLocationSubcategory] = useState('');

  const [error, setError] = useState('');

  const locationTag = locationTerminal && locationSubcategory
    ? `${locationTerminal}-${locationSubcategory}`
    : '';
  const locationSubcategories = locationTerminal ? LOCATION_CATALOG[locationTerminal] : [];

  const mutation = useMutation({
    mutationFn: (data: typeof form) =>
      isEdit
        ? api.patch(`/shift-types/${shiftType!.id}`, data)
        : api.post('/shift-types/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shift-types'] });
      onClose();
    },
    onError: (error: unknown) => setError(getApiErrorMessage(error, 'Error al guardar')),
  });

  const handleChange = (field: string, value: string | number | boolean) =>
    setForm((f) => ({ ...f, [field]: value }));

  const submit = () => {
    setError('');
    const payload = { ...form };

    payload.code = payload.code.trim().toUpperCase().replace(/\s+/g, '');
    payload.name = payload.name.trim();

    if (!isEdit && locationTag) {
      payload.code = form.code.includes(locationTag) ? form.code : `${form.code}-${locationTag}`;
      payload.name = form.name.includes(`(${locationTag})`) ? form.name : `${form.name} (${locationTag})`;
    }

    payload.code = payload.code.trim().toUpperCase().replace(/\s+/g, '');

    if (!SHIFT_CODE_PATTERN.test(payload.code)) {
      setError('Código inválido. Usa formato M|T|N|F-TERMINAL-SUBCAT (ej: M-T123-B25).');
      return;
    }

    if (!payload.name) {
      setError('El nombre es obligatorio');
      return;
    }

    mutation.mutate(payload);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">{isEdit ? 'Editar tipo' : 'Nuevo tipo de turno'}</h2>
          <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
        </div>

        {error && <div className="error-msg">{error}</div>}

        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Código</label>
            <input className="form-input" value={form.code} onChange={(e) => handleChange('code', e.target.value.toUpperCase())} required />
            <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)', marginTop: '0.25rem' }}>
              Formato: M|T|N|F-TERMINAL-SUBCAT (ej: M-T123-B25)
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Nombre</label>
            <input className="form-input" value={form.name} onChange={(e) => handleChange('name', e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">Hora inicio</label>
            <input className="form-input" type="time" value={form.start_time} onChange={(e) => handleChange('start_time', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Hora fin</label>
            <input className="form-input" type="time" value={form.end_time} onChange={(e) => handleChange('end_time', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Duración (horas)</label>
            <input className="form-input" type="number" min={1} max={24} value={form.duration_hours} onChange={(e) => handleChange('duration_hours', Number(e.target.value))} />
          </div>
          <div className="form-group">
            <label className="form-label">Color</label>
            <input className="form-input" type="color" value={form.color} onChange={(e) => handleChange('color', e.target.value)} style={{ height: 38, padding: 2 }} />
          </div>
        </div>

        {!isEdit && (
          <>
            <div className="form-grid" style={{ marginTop: '0.5rem' }}>
              <div className="form-group">
                <label className="form-label">Terminal (opcional)</label>
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
                <label className="form-label">Subcategoría (opcional)</label>
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
            </div>
            {locationTag && (
              <div style={{ fontSize: '0.78rem', color: 'var(--gray-500)', marginTop: '-0.2rem' }}>
                Se guardará con sufijo por ubicación: <strong>{locationTag}</strong>
              </div>
            )}
          </>
        )}

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

/* ─── Assign Employees Modal ──────────────────────────────── */
type DateSelectionMode = 'single' | 'week' | 'month' | 'multiple';

function AssignEmployeesModal({
  shiftType,
  onClose,
}: {
  shiftType: ShiftType;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [dateMode, setDateMode] = useState<DateSelectionMode>('single');
  const [selectedDate, setSelectedDate] = useState(() => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow.toISOString().split('T')[0];
  });
  const [selectedWeek, setSelectedWeek] = useState('');
  const [selectedMonth, setSelectedMonth] = useState('');
  const [multipleDates, setMultipleDates] = useState<string[]>([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>('');
  const [employeeLocationTerminal, setEmployeeLocationTerminal] = useState<LocationTerminal | ''>('');
  const [employeeLocationSubcategory, setEmployeeLocationSubcategory] = useState('');
  const [locationTerminal, setLocationTerminal] = useState<LocationTerminal | ''>('');
  const [locationSubcategory, setLocationSubcategory] = useState('');
  const [selectedEmployeeIds, setSelectedEmployeeIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [assignedCount, setAssignedCount] = useState(0);

  const { data: employees } = useQuery({
    queryKey: ['employees'],
    queryFn: () => api.get<Employee[]>('/employees/').then((r) => r.data),
  });

  const { data: categories } = useQuery({
    queryKey: ['employee-categories'],
    queryFn: () => api.get<EmployeeCategory[]>('/employee-categories/').then((r) => r.data),
  });

  const locationValue = locationTerminal && locationSubcategory
    ? toLocationValue(locationTerminal, locationSubcategory)
    : '';
  const locationSubcategories = locationTerminal ? LOCATION_CATALOG[locationTerminal] : [];

  const employeeLocationValue = employeeLocationTerminal && employeeLocationSubcategory
    ? toLocationValue(employeeLocationTerminal, employeeLocationSubcategory)
    : '';
  const employeeLocationSubcategories = employeeLocationTerminal ? LOCATION_CATALOG[employeeLocationTerminal] : [];

  // Función para obtener array de fechas según el modo seleccionado
  const getDatesArray = (): string[] => {
    switch (dateMode) {
      case 'single':
        return [selectedDate];
      
      case 'week': {
        if (!selectedWeek) return [];
        const [year, weekStr] = selectedWeek.split('-W');
        const week = parseInt(weekStr);
        
        // Calcular el primer día de la semana ISO (lunes)
        const jan4 = new Date(parseInt(year), 0, 4);
        const mondayOfWeek1 = new Date(jan4);
        mondayOfWeek1.setDate(jan4.getDate() - (jan4.getDay() || 7) + 1);
        
        const targetMonday = new Date(mondayOfWeek1);
        targetMonday.setDate(mondayOfWeek1.getDate() + (week - 1) * 7);
        
        const dates: string[] = [];
        for (let i = 0; i < 7; i++) {
          const date = new Date(targetMonday);
          date.setDate(targetMonday.getDate() + i);
          dates.push(date.toISOString().split('T')[0]);
        }
        return dates;
      }
      
      case 'month': {
        if (!selectedMonth) return [];
        const [year, month] = selectedMonth.split('-').map(Number);
        const daysInMonth = new Date(year, month, 0).getDate();
        
        const dates: string[] = [];
        for (let day = 1; day <= daysInMonth; day++) {
          const date = new Date(year, month - 1, day);
          dates.push(date.toISOString().split('T')[0]);
        }
        return dates;
      }
      
      case 'multiple':
        return multipleDates;
      
      default:
        return [];
    }
  };

  const assignMutation = useMutation({
    mutationFn: async (employeeIds: string[]) => {
      const dates = getDatesArray();
      if (dates.length === 0) throw new Error('Debe seleccionar al menos una fecha');
      
      const promises: Promise<unknown>[] = [];
      for (const date of dates) {
        for (const employeeId of employeeIds) {
          promises.push(
            api.post('/assignments/', {
              date,
              employee_id: employeeId,
              shift_type_id: shiftType.id,
              status: 'asignado',
              location: locationValue || undefined,
            })
          );
        }
      }
      return Promise.all(promises);
    },
    onSuccess: (results) => {
      setAssignedCount(results.length);
      setSuccess(true);
      qc.invalidateQueries({ queryKey: ['assignments'] });
      setTimeout(() => onClose(), 1500);
    },
    onError: (error: unknown) => setError(getApiErrorMessage(error, 'Error al asignar empleados')),
  });

  const toggleEmployee = (employeeId: string) => {
    const updated = new Set(selectedEmployeeIds);
    if (updated.has(employeeId)) {
      updated.delete(employeeId);
    } else {
      updated.add(employeeId);
    }
    setSelectedEmployeeIds(updated);
  };

  const handleSubmit = () => {
    if (selectedEmployeeIds.size === 0) {
      setError('Selecciona al menos un empleado');
      return;
    }
    
    const dates = getDatesArray();
    if (dates.length === 0) {
      setError('Selecciona al menos una fecha');
      return;
    }
    
    setError('');
    assignMutation.mutate(Array.from(selectedEmployeeIds));
  };

  const filteredEmployees = employees?.filter((emp) => {
    if (emp.status !== 'activo') return false;
    if (selectedCategoryId && emp.category?.id !== selectedCategoryId) return false;
    if (employeeLocationValue && emp.location !== employeeLocationValue) return false;
    return true;
  }) ?? [];

  if (success) {
    const dates = getDatesArray();
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h2 className="modal-title">✓ Asignación completada</h2>
            <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
          </div>
          <p style={{ padding: '1rem' }}>
            Se crearon <strong>{assignedCount}</strong> asignación(es): <strong>{selectedEmployeeIds.size}</strong> empleado(s) × <strong>{dates.length}</strong> día(s) al turno <strong>{shiftType.code}</strong>.
          </p>
          <div className="modal-footer">
            <button className="btn btn-primary" onClick={onClose}>Cerrar</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-lg" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '700px' }}>
        <div className="modal-header">
          <h2 className="modal-title">Asignar empleados — {shiftType.code}</h2>
          <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
        </div>

        {error && <div className="error-msg">{error}</div>}

        <div style={{ padding: '1.5rem', paddingTop: '1rem' }}>
          {/* Selector de modo de fecha */}
          <div className="form-group" style={{ marginBottom: '1rem' }}>
            <label className="form-label">Modo de selección de fechas</label>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="dateMode"
                  value="single"
                  checked={dateMode === 'single'}
                  onChange={(e) => setDateMode(e.target.value as DateSelectionMode)}
                />
                Día único
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="dateMode"
                  value="week"
                  checked={dateMode === 'week'}
                  onChange={(e) => setDateMode(e.target.value as DateSelectionMode)}
                />
                Semana completa
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="dateMode"
                  value="month"
                  checked={dateMode === 'month'}
                  onChange={(e) => setDateMode(e.target.value as DateSelectionMode)}
                />
                Mes completo
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="dateMode"
                  value="multiple"
                  checked={dateMode === 'multiple'}
                  onChange={(e) => setDateMode(e.target.value as DateSelectionMode)}
                />
                Días específicos
              </label>
            </div>
          </div>

          <div className="form-grid" style={{ gridTemplateColumns: '1fr 1fr', marginBottom: '1rem' }}>
            {/* Input según modo */}
            <div className="form-group">
              <label className="form-label">
                {dateMode === 'single' && 'Fecha'}
                {dateMode === 'week' && 'Semana'}
                {dateMode === 'month' && 'Mes'}
                {dateMode === 'multiple' && 'Seleccionar días'}
              </label>
              
              {dateMode === 'single' && (
                <input
                  type="date"
                  className="form-input"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  min={new Date().toISOString().split('T')[0]}
                />
              )}
              
              {dateMode === 'week' && (
                <input
                  type="week"
                  className="form-input"
                  value={selectedWeek}
                  onChange={(e) => setSelectedWeek(e.target.value)}
                  min={(() => {
                    const today = new Date();
                    const year = today.getFullYear();
                    const weekNum = Math.ceil((today.getTime() - new Date(year, 0, 1).getTime()) / (7 * 24 * 60 * 60 * 1000));
                    return `${year}-W${weekNum.toString().padStart(2, '0')}`;
                  })()}
                />
              )}
              
              {dateMode === 'month' && (
                <input
                  type="month"
                  className="form-input"
                  value={selectedMonth}
                  onChange={(e) => setSelectedMonth(e.target.value)}
                  min={(() => {
                    const today = new Date();
                    return `${today.getFullYear()}-${(today.getMonth() + 1).toString().padStart(2, '0')}`;
                  })()}
                />
              )}
              
              {dateMode === 'multiple' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <input
                      type="date"
                      className="form-input"
                      id="newDateInput"
                      min={new Date().toISOString().split('T')[0]}
                    />
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => {
                        const input = document.getElementById('newDateInput') as HTMLInputElement;
                        if (input?.value && !multipleDates.includes(input.value)) {
                          setMultipleDates([...multipleDates, input.value].sort());
                          input.value = '';
                        }
                      }}
                    >
                      <Plus size={14} />
                    </button>
                  </div>
                  
                  {multipleDates.length > 0 && (
                    <div style={{
                      maxHeight: '120px',
                      overflowY: 'auto',
                      border: '1px solid var(--gray-300)',
                      borderRadius: '4px',
                      padding: '0.5rem',
                      background: 'var(--gray-50)',
                    }}>
                      {multipleDates.map((date) => (
                        <div
                          key={date}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '0.25rem 0',
                            fontSize: '0.9rem',
                          }}
                        >
                          <span>{date}</span>
                          <button
                            type="button"
                            className="btn btn-icon btn-danger btn-sm"
                            onClick={() => setMultipleDates(multipleDates.filter((d) => d !== date))}
                            style={{ padding: '2px 6px' }}
                          >
                            <X size={12} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {multipleDates.length === 0 && (
                    <div style={{ fontSize: '0.8rem', color: 'var(--gray-500)' }}>
                      Agrega días haciendo clic en el botón +
                    </div>
                  )}
                </div>
              )}
            </div>
            
            <div className="form-group">
              <label className="form-label">Filtrar por categoría</label>
              <select
                className="form-select"
                value={selectedCategoryId}
                onChange={(e) => setSelectedCategoryId(e.target.value)}
              >
                <option value="">Todas las categorías</option>
                {categories?.map((cat) => (
                  <option key={cat.id} value={cat.id}>{cat.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-grid" style={{ gridTemplateColumns: '1fr 1fr', marginBottom: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Filtrar por terminal (empleado)</label>
              <select
                className="form-select"
                value={employeeLocationTerminal}
                onChange={(e) => {
                  const terminal = e.target.value as LocationTerminal | '';
                  setEmployeeLocationTerminal(terminal);
                  setEmployeeLocationSubcategory('');
                }}
              >
                <option value="">— Todas —</option>
                {Object.keys(LOCATION_CATALOG).map((terminal) => (
                  <option key={terminal} value={terminal}>{terminal}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Filtrar por subcategoría (empleado)</label>
              <select
                className="form-select"
                value={employeeLocationSubcategory}
                onChange={(e) => setEmployeeLocationSubcategory(e.target.value)}
                disabled={!employeeLocationTerminal}
              >
                <option value="">— Todas —</option>
                {employeeLocationSubcategories.map((subcategory) => (
                  <option key={subcategory} value={subcategory}>{subcategory}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-grid" style={{ gridTemplateColumns: '1fr 1fr', marginBottom: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Terminal de asignación <span style={{ fontWeight: 400, color: 'var(--gray-400)' }}>(opcional)</span></label>
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
              <label className="form-label">Subcategoría de asignación <span style={{ fontWeight: 400, color: 'var(--gray-400)' }}>(opcional)</span></label>
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
          </div>

          {/* Resumen de fechas seleccionadas */}
          {(() => {
            const dates = getDatesArray();
            return dates.length > 0 ? (
              <div style={{
                marginBottom: '1rem',
                padding: '0.5rem 0.75rem',
                background: 'var(--blue-50)',
                border: '1px solid var(--blue-200)',
                borderRadius: '4px',
                fontSize: '0.85rem',
                color: 'var(--blue-700)',
              }}>
                <strong>{dates.length}</strong> día(s) seleccionado(s)
                {dates.length <= 7 && (
                  <span style={{ marginLeft: '0.5rem', color: 'var(--gray-600)' }}>
                    ({dates.join(', ')})
                  </span>
                )}
              </div>
            ) : null;
          })()}

          <div style={{ 
            maxHeight: '400px', 
            overflowY: 'auto', 
            border: '1px solid var(--gray-300)', 
            borderRadius: '4px',
            background: '#fff',
          }}>
            {filteredEmployees.length > 0 ? (
              <table style={{ width: '100%', fontSize: '0.9rem' }}>
                <thead style={{ position: 'sticky', top: 0, background: 'var(--gray-50)', borderBottom: '1px solid var(--gray-300)' }}>
                  <tr>
                    <th style={{ padding: '0.5rem', textAlign: 'left', width: 40 }}>
                      <input
                        type="checkbox"
                        checked={filteredEmployees.length > 0 && filteredEmployees.every((e) => selectedEmployeeIds.has(e.id))}
                        onChange={(ev) => {
                          if (ev.target.checked) {
                            setSelectedEmployeeIds(new Set(filteredEmployees.map((e) => e.id)));
                          } else {
                            setSelectedEmployeeIds(new Set());
                          }
                        }}
                      />
                    </th>
                    <th style={{ padding: '0.5rem', textAlign: 'left' }}>Nombre</th>
                    <th style={{ padding: '0.5rem', textAlign: 'left' }}>Categoría</th>
                    <th style={{ padding: '0.5rem', textAlign: 'left' }}>Tipo agente</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEmployees.map((emp) => (
                    <tr
                      key={emp.id}
                      style={{
                        cursor: 'pointer',
                        background: selectedEmployeeIds.has(emp.id) ? 'var(--blue-50)' : 'transparent',
                      }}
                      onClick={() => toggleEmployee(emp.id)}
                    >
                      <td style={{ padding: '0.5rem' }}>
                        <input
                          type="checkbox"
                          checked={selectedEmployeeIds.has(emp.id)}
                          onChange={() => toggleEmployee(emp.id)}
                        />
                      </td>
                      <td style={{ padding: '0.5rem' }}>
                        <strong>{emp.first_name} {emp.last_name}</strong>
                        <div style={{ fontSize: '0.8rem', color: 'var(--gray-500)' }}>
                          {emp.document_number}
                        </div>
                      </td>
                      <td style={{ padding: '0.5rem' }}>
                        {emp.category ? (
                          <span className="badge badge-blue">{emp.category.name}</span>
                        ) : (
                          <span className="badge badge-gray">Sin categoría</span>
                        )}
                      </td>
                      <td style={{ padding: '0.5rem' }}>
                        {emp.agent_type ? (
                          <span className="badge badge-green">{emp.agent_type.name}</span>
                        ) : (
                          <span className="badge badge-gray">Sin tipo</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--gray-500)' }}>
                No hay empleados activos{selectedCategoryId ? ' en esta categoría' : ''}
              </div>
            )}
          </div>

          <div style={{ marginTop: '1rem', fontSize: '0.9rem', color: 'var(--gray-600)' }}>
            <strong>{selectedEmployeeIds.size}</strong> empleado(s) seleccionado(s)
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancelar</button>
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={assignMutation.isPending || selectedEmployeeIds.size === 0}
          >
            {assignMutation.isPending ? <span className="spinner" /> : `Asignar ${selectedEmployeeIds.size > 0 ? selectedEmployeeIds.size : ''} empleado(s)`}
          </button>
        </div>
      </div>
    </div>
  );
}
