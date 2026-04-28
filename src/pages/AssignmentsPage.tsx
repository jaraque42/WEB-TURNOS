import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../lib/api';
import { getApiErrorMessage } from '../lib/error';
import { LOCATION_CATALOG, LOCATION_OPTIONS, parseLocationValue, toLocationValue, type LocationTerminal } from '../lib/locations';
import type { ShiftAssignment, ShiftType, Employee, EmployeeCategory } from '../types';
import { ChevronLeft, ChevronRight, Plus, X, Trash2, Calendar, CalendarDays, CalendarRange, CheckSquare } from 'lucide-react';

/* ─── Helpers ─────────────────────────────────────────────── */
function startOfMonth(d: Date) { return new Date(d.getFullYear(), d.getMonth(), 1); }
function endOfMonth(d: Date) { return new Date(d.getFullYear(), d.getMonth() + 1, 0); }
function fmt(d: Date) { return d.toISOString().slice(0, 10); }
function addMonths(d: Date, n: number) { return new Date(d.getFullYear(), d.getMonth() + n, 1); }

/** Lunes de la semana que contiene `d` */
function startOfWeek(d: Date) {
  const copy = new Date(d);
  const dow = copy.getDay();
  const diff = dow === 0 ? -6 : 1 - dow;
  copy.setDate(copy.getDate() + diff);
  return copy;
}
function endOfWeek(d: Date) {
  const mon = startOfWeek(d);
  mon.setDate(mon.getDate() + 6);
  return mon;
}

const DAY_NAMES = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
const MONTH_NAMES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];

interface CalendarDay {
  date: Date;
  iso: string;
  isCurrentMonth: boolean;
  isToday: boolean;
}

function buildCalendar(refDate: Date): CalendarDay[] {
  const start = startOfMonth(refDate);
  const end = endOfMonth(refDate);
  const today = fmt(new Date());

  let dow = start.getDay() - 1;
  if (dow < 0) dow = 6;

  const days: CalendarDay[] = [];

  for (let i = dow - 1; i >= 0; i--) {
    const d = new Date(start);
    d.setDate(d.getDate() - i - 1);
    days.push({ date: d, iso: fmt(d), isCurrentMonth: false, isToday: fmt(d) === today });
  }

  for (let i = 1; i <= end.getDate(); i++) {
    const d = new Date(refDate.getFullYear(), refDate.getMonth(), i);
    days.push({ date: d, iso: fmt(d), isCurrentMonth: true, isToday: fmt(d) === today });
  }

  while (days.length % 7 !== 0) {
    const last = days[days.length - 1].date;
    const d = new Date(last);
    d.setDate(d.getDate() + 1);
    days.push({ date: d, iso: fmt(d), isCurrentMonth: false, isToday: fmt(d) === today });
  }

  return days;
}

type AssignMode = 'day' | 'week' | 'range';

/* ═══════════════════════════════════════════════════════════ */
/*  Page                                                       */
/* ═══════════════════════════════════════════════════════════ */
export default function AssignmentsPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [month, setMonth] = useState(new Date());
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedDate, setSelectedDate] = useState('');
  const [detailDate, setDetailDate] = useState<string | null>(null);

  // Modo selección para borrado masivo
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [bulkResult, setBulkResult] = useState<{ deleted: number; skipped: number; details: string[] } | null>(null);
  const [locationFilter, setLocationFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');

  const dateFrom = fmt(startOfMonth(month));
  const dateTo = fmt(endOfMonth(month));
  const employeeId = searchParams.get('employee_id') ?? undefined;

  const { data: assignments } = useQuery({
    queryKey: ['assignments', dateFrom, dateTo, employeeId, locationFilter],
    queryFn: () =>
      api.get<ShiftAssignment[]>('/assignments/', {
        params: {
          date_from: dateFrom,
          date_to: dateTo,
          ...(employeeId ? { employee_id: employeeId } : {}),
          ...(locationFilter ? { location: locationFilter } : {}),
        },
      }).then((r) => r.data),
  });

  const { data: employees } = useQuery({
    queryKey: ['employees'],
    queryFn: () => api.get<Employee[]>('/employees/').then((r) => r.data),
  });

  const { data: shiftTypes } = useQuery({
    queryKey: ['shift-types'],
    queryFn: () => api.get<ShiftType[]>('/shift-types/').then((r) => r.data),
  });

  const { data: categories } = useQuery({
    queryKey: ['employee-categories'],
    queryFn: () => api.get<EmployeeCategory[]>('/employee-categories/').then((r) => r.data),
  });

  // Mapa employee_id → category_id para filtrar asignaciones por categoría
  const employeeCategoryMap = useMemo(() => {
    const m: Record<string, string> = {};
    employees?.forEach((e) => {
      const catId = e.category?.id ?? e.category_id;
      if (catId) m[String(e.id)] = String(catId);
    });
    return m;
  }, [employees]);

  const shiftColorMap = useMemo(() => {
    const m: Record<string, string> = {};
    shiftTypes?.forEach((st) => { m[st.id] = st.color; });
    return m;
  }, [shiftTypes]);

  const filteredEmployee = useMemo(
    () => employees?.find((emp) => emp.id === employeeId) ?? null,
    [employees, employeeId],
  );

  const filteredAssignments = useMemo(() => {
    if (!categoryFilter) return assignments ?? [];
    return (assignments ?? []).filter((a) => employeeCategoryMap[String(a.employee_id)] === categoryFilter);
  }, [assignments, categoryFilter, employeeCategoryMap]);

  const assignmentsByDate = useMemo(() => {
    const m: Record<string, ShiftAssignment[]> = {};
    filteredAssignments.forEach((a) => { (m[a.date] ??= []).push(a); });
    return m;
  }, [filteredAssignments]);

  const calendarDays = useMemo(() => buildCalendar(month), [month]);

  const openCreate = (date: string) => {
    if (selectMode) return;
    setSelectedDate(date);
    setShowCreateModal(true);
  };

  const openDetail = (date: string, e: React.MouseEvent) => {
    if (selectMode) return;
    e.stopPropagation();
    setDetailDate(date);
  };

  // ── Selección masiva ──
  const isSelected = (id: string) => selectedIds.includes(id);

  const toggleSelectMode = () => {
    if (selectMode) {
      setSelectMode(false);
      setSelectedIds([]);
      setBulkResult(null);
    } else {
      setSelectMode(true);
      setSelectedIds([]);
      setBulkResult(null);
    }
  };

  const toggleAssignment = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const toggleAllDay = (dayIso: string) => {
    const dayAssignments = assignmentsByDate[dayIso] ?? [];
    if (dayAssignments.length === 0) return;
    const ids = dayAssignments.map((a) => a.id);
    setSelectedIds((prev) => {
      const allSelected = ids.every((id) => prev.includes(id));
      if (allSelected) return prev.filter((id) => !ids.includes(id));
      const merged = [...prev];
      ids.forEach((id) => { if (!merged.includes(id)) merged.push(id); });
      return merged;
    });
  };

  const selectAllMonth = () => {
    if (!filteredAssignments) return;
    setSelectedIds(filteredAssignments.map((a) => a.id));
  };

  const deselectAllMonth = () => setSelectedIds([]);

  const handleBulkDelete = async () => {
    if (selectedIds.length === 0) return;
    if (!confirm(`¿Eliminar ${selectedIds.length} asignación${selectedIds.length > 1 ? 'es' : ''}?`)) return;
    setBulkDeleting(true);
    try {
      const res = await api.post<{ deleted: number; skipped: number; details: string[] }>(
        '/assignments/bulk-delete',
        { assignment_ids: selectedIds },
      );
      setBulkResult(res.data);
      setSelectedIds([]);
      qc.invalidateQueries({ queryKey: ['assignments'] });
    } catch {
      alert('Error al eliminar asignaciones');
    } finally {
      setBulkDeleting(false);
    }
  };

  return (
    <>
      <div className="header">
        <h1 className="header-title">Asignaciones</h1>
        <div className="header-actions">
          <select
            className="form-select"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            style={{ width: 190 }}
            title="Filtrar por categoría"
          >
            <option value="">Todas las categorías</option>
            {categories?.map((cat) => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
          <select
            className="form-select"
            value={locationFilter}
            onChange={(e) => setLocationFilter(e.target.value)}
            style={{ width: 210 }}
            title="Filtrar por ubicación"
          >
            <option value="">Todas las ubicaciones</option>
            {LOCATION_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          {employeeId && (
            <>
              <span style={{ fontSize: '0.82rem', color: 'var(--gray-600)' }}>
                {filteredEmployee
                  ? `Empleado: ${filteredEmployee.last_name}, ${filteredEmployee.first_name}`
                  : 'Empleado filtrado'}
              </span>
              <button className="btn btn-secondary btn-sm" onClick={() => navigate('/assignments')}>
                Ver todos
              </button>
            </>
          )}
          <button className="btn btn-secondary btn-sm" onClick={() => setMonth(addMonths(month, -1))}>
            <ChevronLeft size={16} />
          </button>
          <span style={{ fontWeight: 600, minWidth: 160, textAlign: 'center', display: 'inline-block' }}>
            {MONTH_NAMES[month.getMonth()]} {month.getFullYear()}
          </span>
          <button className="btn btn-secondary btn-sm" onClick={() => setMonth(addMonths(month, 1))}>
            <ChevronRight size={16} />
          </button>
          <button
            type="button"
            className={`btn btn-sm ${selectMode ? 'btn-danger' : 'btn-secondary'}`}
            onClick={toggleSelectMode}
            title={selectMode ? 'Salir de selección' : 'Seleccionar para eliminar'}
          >
            <CheckSquare size={16} /> {selectMode ? 'Cancelar' : 'Seleccionar'}
          </button>
          {!selectMode && (
            <button className="btn btn-primary" onClick={() => openCreate(fmt(new Date()))}>
              <Plus size={16} /> Nueva asignación
            </button>
          )}
        </div>
      </div>

      {/* Barra de selección masiva */}
      {selectMode && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.6rem 1.25rem',
          background: selectedIds.length > 0 ? '#fef2f2' : '#fffbeb',
          borderBottom: '2px solid var(--danger)',
          position: 'sticky', top: 56, zIndex: 49, flexWrap: 'wrap',
        }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>
            {selectedIds.length} asignación{selectedIds.length !== 1 ? 'es' : ''} seleccionada{selectedIds.length !== 1 ? 's' : ''}
          </span>
          <button className="btn btn-secondary btn-sm" onClick={selectAllMonth} style={{ fontSize: '0.75rem' }}>
            Seleccionar todo el mes
          </button>
          <button className="btn btn-secondary btn-sm" onClick={deselectAllMonth} style={{ fontSize: '0.75rem' }}>
            Deseleccionar todo
          </button>
          <div style={{ flex: 1 }} />
          <button
            className="btn btn-danger btn-sm"
            onClick={handleBulkDelete}
            disabled={selectedIds.length === 0 || bulkDeleting}
            style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}
          >
            {bulkDeleting ? <span className="spinner" /> : <Trash2 size={14} />}
            Eliminar seleccionadas ({selectedIds.length})
          </button>
        </div>
      )}

      <div className="page-content" style={selectMode ? { background: '#fefce8' } : undefined}>
        {selectMode && (
          <div style={{ padding: '0.5rem 0 0.25rem', textAlign: 'center', fontSize: '0.8rem', color: '#b45309', fontWeight: 500 }}>
            Modo selección activo — haz click en los turnos o días para seleccionarlos
          </div>
        )}
        <div className="calendar-grid">
          {DAY_NAMES.map((d) => (
            <div key={d} className="calendar-header-cell">{d}</div>
          ))}
          {calendarDays.map((day) => {
            const dayAssignments = assignmentsByDate[day.iso] ?? [];
            const daySelectedCount = dayAssignments.filter((a) => isSelected(a.id)).length;
            const allDaySelected = dayAssignments.length > 0 && daySelectedCount === dayAssignments.length;
            return (
              <div
                key={day.iso}
                className={`calendar-cell${day.isCurrentMonth ? '' : ' other-month'}${day.isToday ? ' today' : ''}`}
                onClick={() => selectMode ? toggleAllDay(day.iso) : openCreate(day.iso)}
                style={{
                  cursor: 'pointer', position: 'relative',
                  outline: selectMode && daySelectedCount > 0 ? '2px solid var(--danger)' : undefined,
                  outlineOffset: '-2px',
                  background: selectMode && allDaySelected ? '#fee2e2' : undefined,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div className="calendar-day-number">{day.date.getDate()}</div>
                  {selectMode && dayAssignments.length > 0 ? (
                    <input
                      type="checkbox"
                      checked={allDaySelected}
                      onChange={() => toggleAllDay(day.iso)}
                      onClick={(e) => e.stopPropagation()}
                      style={{ width: 14, height: 14, cursor: 'pointer', accentColor: 'var(--danger)' }}
                      title="Seleccionar todo el día"
                    />
                  ) : !selectMode && dayAssignments.length > 0 ? (
                    <span
                      title="Ver asignaciones del día"
                      onClick={(e) => openDetail(day.iso, e)}
                      style={{
                        fontSize: '0.65rem', background: 'var(--gray-200)', borderRadius: '50%',
                        width: 18, height: 18, display: 'flex', alignItems: 'center', justifyContent: 'center',
                        cursor: 'pointer', fontWeight: 700, color: 'var(--gray-600)',
                      }}
                    >
                      {dayAssignments.length}
                    </span>
                  ) : null}
                </div>
                {dayAssignments.slice(0, 3).map((a) => {
                  const sel = isSelected(a.id);
                  return (
                    <div
                      key={a.id}
                      className="calendar-event"
                      style={{
                        background: selectMode && sel
                          ? '#ef4444'
                          : shiftColorMap[a.shift_type_id] ?? '#6b7280',
                        opacity: selectMode && !sel ? 0.6 : 1,
                      }}
                      title={`${a.employee_name} — ${a.shift_type_name}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (selectMode) toggleAssignment(a.id);
                        else openDetail(day.iso, e);
                      }}
                    >
                      {selectMode && (
                        <input
                          type="checkbox"
                          checked={sel}
                          readOnly
                          style={{ width: 11, height: 11, marginRight: 3, pointerEvents: 'none', accentColor: '#fff' }}
                        />
                      )}
                      {a.shift_type_code} {a.employee_name?.split(',')[0]}
                    </div>
                  );
                })}
                {dayAssignments.length > 3 && (
                  <div
                    style={{ fontSize: '0.7rem', color: 'var(--gray-500)', textAlign: 'center', cursor: 'pointer' }}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (!selectMode) openDetail(day.iso, e);
                      else toggleAllDay(day.iso);
                    }}
                  >
                    +{dayAssignments.length - 3} más
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Modal crear asignación */}
      {showCreateModal && (
        <CreateAssignmentModal
          date={selectedDate}
          shiftTypes={shiftTypes ?? []}
          initialEmployeeId={employeeId}
          onClose={() => setShowCreateModal(false)}
        />
      )}

      {/* Panel detalle del día */}
      {detailDate && (
        <DayDetailModal
          date={detailDate}
          assignments={assignmentsByDate[detailDate] ?? []}
          shiftColorMap={shiftColorMap}
          onClose={() => setDetailDate(null)}
          onDelete={(id) => {
            api.delete(`/assignments/${id}`).then(() => {
              qc.invalidateQueries({ queryKey: ['assignments'] });
              const remaining = (assignmentsByDate[detailDate] ?? []).filter((a) => a.id !== id);
              if (remaining.length === 0) setDetailDate(null);
            });
          }}
        />
      )}

      {/* Resultado de borrado masivo */}
      {bulkResult && (
        <div className="modal-overlay" onClick={() => setBulkResult(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 420 }}>
            <div className="modal-header">
              <h2 className="modal-title">Resultado de eliminación</h2>
              <button className="btn btn-icon btn-secondary btn-sm" onClick={() => setBulkResult(null)}><X size={16} /></button>
            </div>
            <div style={{ padding: '0.5rem 0' }}>
              <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.75rem' }}>
                <div style={{ flex: 1, padding: '0.75rem', background: '#dcfce7', borderRadius: 'var(--radius)', textAlign: 'center' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#16a34a' }}>{bulkResult.deleted}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--gray-600)' }}>Eliminadas</div>
                </div>
                {bulkResult.skipped > 0 && (
                  <div style={{ flex: 1, padding: '0.75rem', background: '#fef9c3', borderRadius: 'var(--radius)', textAlign: 'center' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#ca8a04' }}>{bulkResult.skipped}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--gray-600)' }}>Omitidas</div>
                  </div>
                )}
              </div>
              {bulkResult.details.length > 0 && (
                <details style={{ fontSize: '0.8rem', color: 'var(--gray-600)' }}>
                  <summary style={{ cursor: 'pointer', fontWeight: 500 }}>Detalles ({bulkResult.details.length})</summary>
                  <ul style={{ paddingLeft: '1.2rem', maxHeight: 160, overflow: 'auto' }}>
                    {bulkResult.details.map((d, i) => <li key={i}>{d}</li>)}
                  </ul>
                </details>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={() => { setBulkResult(null); setSelectMode(false); }}>Cerrar</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ═══════════════════════════════════════════════════════════ */
/*  Day Detail Modal                                           */
/* ═══════════════════════════════════════════════════════════ */
function DayDetailModal({
  date,
  assignments,
  shiftColorMap,
  onClose,
  onDelete,
}: {
  date: string;
  assignments: ShiftAssignment[];
  shiftColorMap: Record<string, string>;
  onClose: () => void;
  onDelete: (id: string) => void;
}) {
  const [deleting, setDeleting] = useState<string | null>(null);

  const handleDelete = (id: string) => {
    if (!confirm('¿Eliminar esta asignación?')) return;
    setDeleting(id);
    onDelete(id);
  };

  const dateLabel = new Date(date + 'T12:00:00').toLocaleDateString('es-AR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520 }}>
        <div className="modal-header">
          <h2 className="modal-title" style={{ textTransform: 'capitalize' }}>{dateLabel}</h2>
          <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
        </div>

        {assignments.length === 0 ? (
          <p style={{ padding: '1rem', color: 'var(--gray-500)' }}>Sin asignaciones</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '0.5rem 0' }}>
            {assignments.map((a) => (
              <div
                key={a.id}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '0.6rem 0.75rem', borderRadius: 'var(--radius)',
                  background: 'var(--gray-50)', border: '1px solid var(--gray-200)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <span
                    style={{
                      display: 'inline-block', width: 10, height: 10, borderRadius: '50%',
                      background: shiftColorMap[a.shift_type_id] ?? '#6b7280', flexShrink: 0,
                    }}
                  />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{a.employee_name ?? 'Sin nombre'}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--gray-500)' }}>
                      {a.shift_type_code} — {a.shift_type_name}
                      {a.location ? ` · ${formatLocationLabel(a.location)}` : ''}
                    </div>
                  </div>
                </div>
                <button
                  className="btn btn-icon btn-danger btn-sm"
                  title="Eliminar asignación"
                  disabled={deleting === a.id}
                  onClick={() => handleDelete(a.id)}
                >
                  {deleting === a.id ? <span className="spinner" /> : <Trash2 size={14} />}
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cerrar</button>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════ */
/*  Create Assignment Modal                                    */
/* ═══════════════════════════════════════════════════════════ */
function CreateAssignmentModal({
  date,
  shiftTypes,
  initialEmployeeId,
  onClose,
}: {
  date: string;
  shiftTypes: ShiftType[];
  initialEmployeeId?: string;
  onClose: () => void;
}) {
  const qc = useQueryClient();

  const { data: employees } = useQuery({
    queryKey: ['employees'],
    queryFn: () => api.get<Employee[]>('/employees/').then((r) => r.data),
  });

  const { data: categories } = useQuery({
    queryKey: ['employee-categories'],
    queryFn: () => api.get<EmployeeCategory[]>('/employee-categories/').then((r) => r.data),
  });

  const [mode, setMode] = useState<AssignMode>('day');
  const [filterCategoryId, setFilterCategoryId] = useState<string>('');
  const [selectedEmployees, setSelectedEmployees] = useState<string[]>(initialEmployeeId ? [initialEmployeeId] : []);
  const [form, setForm] = useState({
    shift_type_id: shiftTypes[0]?.id ?? '',
    date,
    start_date: date,
    end_date: date,
    notes: '',
  });
  const [locationTerminal, setLocationTerminal] = useState<LocationTerminal | ''>('');
  const [locationSubcategory, setLocationSubcategory] = useState('');
  const [error, setError] = useState('');
  const [result, setResult] = useState<{ created: number; skipped: number; details: string[] } | null>(null);

  const locationValue = locationTerminal && locationSubcategory
    ? toLocationValue(locationTerminal, locationSubcategory)
    : '';
  const locationSubcategories = locationTerminal ? LOCATION_CATALOG[locationTerminal] : [];

  const computedRange = useMemo(() => {
    const d = new Date(form.date + 'T12:00:00');
    if (mode === 'day') return { start: form.date, end: form.date };
    if (mode === 'week') return { start: fmt(startOfWeek(d)), end: fmt(endOfWeek(d)) };
    return { start: form.start_date, end: form.end_date };
  }, [mode, form.date, form.start_date, form.end_date]);

  const toggleEmployee = (id: string) => {
    setSelectedEmployees((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const filteredEmployees = employees?.filter((e) => {
    if (e.status !== 'activo') return false;
    if (filterCategoryId && e.category?.id !== filterCategoryId) return false;
    return true;
  }) ?? [];

  const selectAll = () => {
    setSelectedEmployees(filteredEmployees.map((e) => e.id));
  };

  const deselectAll = () => setSelectedEmployees([]);

  const singleMut = useMutation({
    mutationFn: (data: { employee_id: string; shift_type_id: string; date: string; notes: string; location: string }) =>
      api.post('/assignments/', data),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['assignments'], refetchType: 'active' });
      onClose();
    },
    onError: (error: unknown) => setError(getApiErrorMessage(error, 'Error al crear')),
  });

  const bulkMut = useMutation({
    mutationFn: (data: { start_date: string; end_date: string; employee_ids: string[]; shift_type_id: string; location?: string }) =>
      api.post<{ created: number; skipped: number; details: string[] }>('/assignments/bulk', data),
    onSuccess: async (res) => {
      await qc.invalidateQueries({ queryKey: ['assignments'], refetchType: 'active' });
      setResult(res.data);
    },
    onError: (error: unknown) => setError(getApiErrorMessage(error, 'Error al crear asignaciones')),
  });

  const submit = () => {
    setError('');
    if (selectedEmployees.length === 0) {
      setError('Selecciona al menos un empleado');
      return;
    }
    if (!form.shift_type_id) {
      setError('Selecciona un tipo de turno');
      return;
    }

    if (mode === 'day' && selectedEmployees.length === 1) {
      singleMut.mutate({
        employee_id: selectedEmployees[0],
        shift_type_id: form.shift_type_id,
        date: form.date,
        notes: form.notes,
        location: locationValue,
      });
    } else {
      bulkMut.mutate({
        start_date: computedRange.start,
        end_date: computedRange.end,
        employee_ids: selectedEmployees,
        shift_type_id: form.shift_type_id,
        location: locationValue || undefined,
      });
    }
  };

  const isPending = singleMut.isPending || bulkMut.isPending;

  const handleChange = (field: string, value: string) => setForm((f) => ({ ...f, [field]: value }));

  const rangeLabel = useMemo(() => {
    const s = new Date(computedRange.start + 'T12:00:00');
    const e = new Date(computedRange.end + 'T12:00:00');
    const opts: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short' };
    const days = Math.round((e.getTime() - s.getTime()) / 86400000) + 1;
    return `${s.toLocaleDateString('es-AR', opts)} → ${e.toLocaleDateString('es-AR', opts)} (${days} día${days > 1 ? 's' : ''})`;
  }, [computedRange]);

  if (result) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 480 }}>
          <div className="modal-header">
            <h2 className="modal-title">Resultado de asignación</h2>
            <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
          </div>
          <div style={{ padding: '0.5rem 0' }}>
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.75rem' }}>
              <div style={{ flex: 1, padding: '0.75rem', background: '#dcfce7', borderRadius: 'var(--radius)', textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#16a34a' }}>{result.created}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--gray-600)' }}>Creadas</div>
              </div>
              <div style={{ flex: 1, padding: '0.75rem', background: '#fef9c3', borderRadius: 'var(--radius)', textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#ca8a04' }}>{result.skipped}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--gray-600)' }}>Omitidas</div>
              </div>
            </div>
            {result.details.length > 0 && (
              <details style={{ fontSize: '0.8rem', color: 'var(--gray-600)' }}>
                <summary style={{ cursor: 'pointer', fontWeight: 500, marginBottom: '0.25rem' }}>
                  Detalles ({result.details.length})
                </summary>
                <ul style={{ paddingLeft: '1.2rem', maxHeight: 160, overflow: 'auto' }}>
                  {result.details.map((d, i) => <li key={i}>{d}</li>)}
                </ul>
              </details>
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
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 600 }}>
        <div className="modal-header">
          <h2 className="modal-title">Nueva asignación</h2>
          <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
        </div>

        {error && <div className="error-msg">{error}</div>}

        {/* Modo de asignación */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          {([
            { key: 'day', icon: Calendar, label: 'Día' },
            { key: 'week', icon: CalendarDays, label: 'Semana' },
            { key: 'range', icon: CalendarRange, label: 'Rango' },
          ] as const).map(({ key, icon: Icon, label }) => (
            <button
              key={key}
              className={`btn btn-sm ${mode === key ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setMode(key)}
              style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.3rem' }}
            >
              <Icon size={14} /> {label}
            </button>
          ))}
        </div>

        {/* Fechas según modo */}
        {mode === 'day' && (
          <div className="form-group">
            <label className="form-label">Fecha</label>
            <input className="form-input" type="date" value={form.date} onChange={(e) => handleChange('date', e.target.value)} />
          </div>
        )}
        {mode === 'week' && (
          <div className="form-group">
            <label className="form-label">Semana que contiene</label>
            <input className="form-input" type="date" value={form.date} onChange={(e) => handleChange('date', e.target.value)} />
            <div style={{ fontSize: '0.78rem', color: 'var(--gray-500)', marginTop: '0.25rem' }}>{rangeLabel}</div>
          </div>
        )}
        {mode === 'range' && (
          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Desde</label>
              <input className="form-input" type="date" value={form.start_date} onChange={(e) => handleChange('start_date', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Hasta</label>
              <input className="form-input" type="date" value={form.end_date} onChange={(e) => handleChange('end_date', e.target.value)} />
            </div>
            <div style={{ gridColumn: '1/-1', fontSize: '0.78rem', color: 'var(--gray-500)' }}>{rangeLabel}</div>
          </div>
        )}

        {/* Turno */}
        <div className="form-group">
          <label className="form-label">Tipo de turno</label>
          <select className="form-select" value={form.shift_type_id} onChange={(e) => handleChange('shift_type_id', e.target.value)}>
            {shiftTypes.map((st) => (
              <option key={st.id} value={st.id}>{st.code} — {st.name}</option>
            ))}
          </select>
        </div>

        {/* Ubicación */}
        <div className="form-grid">
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
        </div>

        {mode === 'day' && (
          <div className="form-group">
            <label className="form-label">Notas <span style={{ fontWeight: 400, color: 'var(--gray-400)' }}>(opcional)</span></label>
            <input className="form-input" value={form.notes} onChange={(e) => handleChange('notes', e.target.value)} />
          </div>
        )}

        {/* Filtro por categoría */}
        <div className="form-group">
          <label className="form-label">Filtrar por categoría</label>
          <select
            className="form-select"
            value={filterCategoryId}
            onChange={(e) => setFilterCategoryId(e.target.value)}
          >
            <option value="">Todas las categorías</option>
            {categories?.map((cat) => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
        </div>

        {/* Empleados */}
        <div className="form-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
            <label className="form-label" style={{ marginBottom: 0 }}>
              Empleados ({selectedEmployees.length} seleccionados)
            </label>
            <div style={{ display: 'flex', gap: '0.4rem' }}>
              <button className="btn btn-secondary btn-sm" type="button" onClick={selectAll} style={{ fontSize: '0.72rem', padding: '0.15rem 0.5rem' }}>
                Todos
              </button>
              <button className="btn btn-secondary btn-sm" type="button" onClick={deselectAll} style={{ fontSize: '0.72rem', padding: '0.15rem 0.5rem' }}>
                Ninguno
              </button>
            </div>
          </div>
          <div
            style={{
              border: '1px solid var(--gray-200)', borderRadius: 'var(--radius)',
              maxHeight: 200, overflow: 'auto', padding: '0.35rem',
            }}
          >
            {filteredEmployees.length > 0 ? filteredEmployees.map((emp) => (
              <label
                key={emp.id}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem',
                  padding: '0.3rem 0.5rem', borderRadius: 4, cursor: 'pointer',
                  background: selectedEmployees.includes(emp.id) ? '#eff6ff' : 'transparent',
                  fontSize: '0.82rem',
                }}
              >
                <input
                  type="checkbox"
                  checked={selectedEmployees.includes(emp.id)}
                  onChange={() => toggleEmployee(emp.id)}
                />
                <span style={{ fontWeight: 500 }}>{emp.employee_number}</span>
                <span style={{ color: 'var(--gray-600)' }}>— {emp.last_name}, {emp.first_name}</span>
                {emp.category && <span className="badge badge-blue" style={{ fontSize: '0.7rem', marginLeft: 'auto' }}>{emp.category.name}</span>}
              </label>
            )) : (
              <div style={{ padding: '0.5rem', color: 'var(--gray-400)', fontSize: '0.82rem' }}>No hay empleados activos{filterCategoryId ? ' en esta categoría' : ''}</div>
            )}
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancelar</button>
          <button className="btn btn-primary" onClick={submit} disabled={isPending || selectedEmployees.length === 0}>
            {isPending ? <span className="spinner" /> : `Asignar ${selectedEmployees.length > 0 ? `(${selectedEmployees.length})` : ''}`}
          </button>
        </div>
      </div>
    </div>
  );
}

function formatLocationLabel(location: string): string {
  const parsed = parseLocationValue(location);
  if (!parsed) return location;
  return `${parsed.terminal} · ${parsed.subcategory}`;
}
