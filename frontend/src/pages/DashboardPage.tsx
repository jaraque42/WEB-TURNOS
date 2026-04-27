import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import type { Employee, ShiftType, ShiftAssignment, AssignmentStats } from '../types';
import { Users, Clock, CalendarDays, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/useAuth';
import { getApiErrorMessage } from '../lib/error';

export default function DashboardPage() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const isSuperuser = user?.is_superuser ?? false;

  const { data: employees } = useQuery({
    queryKey: ['employees'],
    queryFn: () => api.get<Employee[]>('/employees/').then((r) => r.data),
  });

  const { data: shiftTypes } = useQuery({
    queryKey: ['shift-types'],
    queryFn: () => api.get<ShiftType[]>('/shift-types/').then((r) => r.data),
  });

  const today = new Date().toISOString().slice(0, 10);
  const { data: todayAssignments } = useQuery({
    queryKey: ['assignments-today'],
    queryFn: () =>
      api.get<ShiftAssignment[]>('/assignments/', { params: { date_from: today, date_to: today } }).then((r) => r.data),
  });

  const { data: stats } = useQuery({
    queryKey: ['assignment-stats'],
    queryFn: () =>
      api.get<AssignmentStats>('/assignments/stats', { params: { date_from: today, date_to: today } }).then((r) => r.data),
  });

  const { data: agentStatus } = useQuery({
    queryKey: ['agent-status'],
    queryFn: () => api.get<{ running: boolean; pid?: number | null }>('/system/agent/status').then((r) => r.data),
    enabled: isSuperuser,
    retry: false,
  });

  const startAgentMut = useMutation({
    mutationFn: () => api.post<{ started: boolean; message: string; pid?: number }>('/system/agent/start'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agent-status'] }),
  });

  return (
    <>
      <div className="header">
        <h1 className="header-title">Dashboard</h1>
        {isSuperuser && (
          <div className="header-actions">
            <button
              className="btn btn-secondary"
              onClick={() => startAgentMut.mutate()}
              disabled={startAgentMut.isPending || Boolean(agentStatus?.running)}
            >
              {startAgentMut.isPending ? 'Iniciando agente...' : agentStatus?.running ? `Agente activo (PID ${agentStatus?.pid ?? '—'})` : 'Levantar agente'}
            </button>
          </div>
        )}
      </div>
      <div className="page-content">
        {isSuperuser && startAgentMut.isError && (
          <div className="card" style={{ marginBottom: '1rem' }}>
            <div className="error-msg">{getApiErrorMessage(startAgentMut.error, 'Error al iniciar agente')}</div>
          </div>
        )}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon blue"><Users size={24} /></div>
            <div>
              <div className="stat-value">{employees?.length ?? '—'}</div>
              <div className="stat-label">Empleados activos</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon green"><Clock size={24} /></div>
            <div>
              <div className="stat-value">{shiftTypes?.length ?? '—'}</div>
              <div className="stat-label">Tipos de turno</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon yellow"><CalendarDays size={24} /></div>
            <div>
              <div className="stat-value">{todayAssignments?.length ?? '—'}</div>
              <div className="stat-label">Asignaciones hoy</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon red"><ShieldCheck size={24} /></div>
            <div>
              <div className="stat-value">{stats?.employees_assigned ?? '—'}</div>
              <div className="stat-label">Empleados asignados hoy</div>
            </div>
          </div>
        </div>

        {/* Recent assignments */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Asignaciones de hoy</h2>
          </div>
          {todayAssignments && todayAssignments.length > 0 ? (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Empleado</th>
                    <th>Turno</th>
                    <th>Estado</th>
                    <th>Ubicación</th>
                  </tr>
                </thead>
                <tbody>
                  {todayAssignments.map((a) => (
                    <tr key={a.id}>
                      <td>{a.employee_name ?? '—'}</td>
                      <td>
                        <span className="badge badge-blue">{a.shift_type_code}</span>{' '}
                        {a.shift_type_name}
                      </td>
                      <td>
                        <span className={`badge ${statusBadge(a.status)}`}>{a.status}</span>
                      </td>
                      <td>{a.location ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">No hay asignaciones para hoy</div>
          )}
        </div>
      </div>
    </>
  );
}

function statusBadge(status: string) {
  switch (status) {
    case 'asignado': return 'badge-blue';
    case 'confirmado': return 'badge-green';
    case 'completado': return 'badge-gray';
    case 'cancelado': return 'badge-red';
    default: return 'badge-yellow';
  }
}
