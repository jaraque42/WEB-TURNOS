import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import ChangePasswordModal from './ChangePasswordModal';
import {
  LayoutDashboard,
  Users,
  UserCog,
  Clock,
  CalendarDays,
  ShieldCheck,
  LogOut,
  KeyRound,
} from 'lucide-react';

const links = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/employees', label: 'Empleados', icon: Users },
  { to: '/shift-types', label: 'Tipos de Turno', icon: Clock },
  { to: '/assignments', label: 'Asignaciones', icon: CalendarDays },
  { to: '/business-rules', label: 'Reglas', icon: ShieldCheck },
  { to: '/imports', label: 'Importar', icon: CalendarDays },
  { to: '/users', label: 'Usuarios', icon: UserCog },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showChangePwd, setShowChangePwd] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <CalendarDays size={22} /> Gestión de Turnos
        </div>
        <nav className="sidebar-nav">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === '/'}
              className={({ isActive }) =>
                `sidebar-link${isActive ? ' active' : ''}`
              }
            >
              <l.icon size={18} /> {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div style={{ marginBottom: '0.5rem' }}>
            <strong>{user?.full_name}</strong>
            <br />
            <span style={{ fontSize: '0.75rem' }}>{user?.email}</span>
          </div>
          <button className="sidebar-link" onClick={() => setShowChangePwd(true)}>
            <KeyRound size={18} /> Cambiar contraseña
          </button>
          <button className="sidebar-link" onClick={handleLogout}>
            <LogOut size={18} /> Cerrar sesión
          </button>
        </div>
      </aside>

      <div className="main-content">
        <Outlet />
      </div>

      {showChangePwd && (
        <ChangePasswordModal onClose={() => setShowChangePwd(false)} />
      )}
    </div>
  );
}
