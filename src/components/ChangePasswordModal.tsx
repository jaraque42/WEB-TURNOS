import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import api from '../lib/api';
import { getApiErrorMessage } from '../lib/error';
import { X } from 'lucide-react';

export default function ChangePasswordModal({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const mutation = useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) =>
      api.post('/users/me/change-password', data),
    onSuccess: () => setSuccess(true),
    onError: (error: unknown) => setError(getApiErrorMessage(error, 'Error al cambiar contraseña')),
  });

  const submit = () => {
    setError('');
    if (form.new_password !== form.confirm_password) {
      setError('Las contraseñas no coinciden');
      return;
    }
    if (form.new_password.length < 4) {
      setError('La contraseña debe tener al menos 4 caracteres');
      return;
    }
    mutation.mutate({
      current_password: form.current_password,
      new_password: form.new_password,
    });
  };

  if (success) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h2 className="modal-title">Contraseña actualizada</h2>
            <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
          </div>
          <p>Tu contraseña fue cambiada correctamente.</p>
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
          <h2 className="modal-title">Cambiar mi contraseña</h2>
          <button className="btn btn-icon btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
        </div>

        {error && <div className="error-msg">{error}</div>}

        <div className="form-group">
          <label className="form-label">Contraseña actual</label>
          <input
            className="form-input"
            type="password"
            value={form.current_password}
            onChange={(e) => setForm((f) => ({ ...f, current_password: e.target.value }))}
            autoFocus
          />
        </div>
        <div className="form-group">
          <label className="form-label">Nueva contraseña</label>
          <input
            className="form-input"
            type="password"
            value={form.new_password}
            onChange={(e) => setForm((f) => ({ ...f, new_password: e.target.value }))}
          />
        </div>
        <div className="form-group">
          <label className="form-label">Confirmar nueva contraseña</label>
          <input
            className="form-input"
            type="password"
            value={form.confirm_password}
            onChange={(e) => setForm((f) => ({ ...f, confirm_password: e.target.value }))}
          />
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancelar</button>
          <button className="btn btn-primary" onClick={submit} disabled={mutation.isPending}>
            {mutation.isPending ? <span className="spinner" /> : 'Cambiar contraseña'}
          </button>
        </div>
      </div>
    </div>
  );
}
