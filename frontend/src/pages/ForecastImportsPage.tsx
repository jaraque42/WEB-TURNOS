import { useMemo, useState } from 'react';
import { useAuth } from '../context/useAuth';
import api from '../lib/api';

// Gráfico Manhattan simple con SVG apilado por grupo
function ManhattanChart({ labels, series }: { labels: string[]; series: { name: string; data: number[] }[] }) {
  const width = Math.max(800, labels.length * 24);
  const height = 360;
  const padding = { left: 60, right: 20, top: 20, bottom: 60 };

  const totals = labels.map((_, i) => series.reduce((acc, s) => acc + (s.data[i] || 0), 0));
  const maxY = Math.max(1, ...totals);

  const xScale = (i: number) => padding.left + i * ((width - padding.left - padding.right) / labels.length) + 4;
  const barWidth = Math.max(8, (width - padding.left - padding.right) / labels.length - 8);
  const yScale = (v: number) => height - padding.bottom - (v / maxY) * (height - padding.top - padding.bottom);

  const colors = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
  ];

  return (
    <div style={{ overflowX: 'auto' }}>
      <svg width={width} height={height}>
        {/* Ejes */}
        <line x1={padding.left} y1={height - padding.bottom} x2={width - padding.right} y2={height - padding.bottom} stroke="#333" />
        <line x1={padding.left} y1={padding.top} x2={padding.left} y2={height - padding.bottom} stroke="#333" />
        {/* Ticks Y */}
        {Array.from({ length: 5 }).map((_, i) => {
          const v = (maxY / 4) * i;
          const y = yScale(v);
          return (
            <g key={i}>
              <line x1={padding.left - 4} y1={y} x2={width - padding.right} y2={y} stroke="#eee" />
              <text x={padding.left - 8} y={y + 4} textAnchor="end" fontSize="10">{Math.round(v)}</text>
            </g>
          );
        })}
        {/* Barras apiladas por fecha */}
        {labels.map((lab, i) => {
          let yBase = height - padding.bottom;
          return (
            <g key={lab}>
              {series.map((s, si) => {
                const yTop = yScale((totals[i] - (series.slice(si + 1).reduce((a, ss) => a + (ss.data[i] || 0), 0))));
                const h = yBase - yTop;
                const x = xScale(i);
                const color = colors[si % colors.length];
                yBase = yTop;
                return (
                  <rect key={s.name} x={x} y={yTop} width={barWidth} height={h} fill={color} />
                );
              })}
              {/* Label X */}
              <text x={xScale(i) + barWidth / 2} y={height - padding.bottom + 14} textAnchor="middle" fontSize="10" fill="#333" transform={`rotate(45 ${xScale(i) + barWidth / 2},${height - padding.bottom + 14})`}>
                {lab.substring(5)}
              </text>
            </g>
          );
        })}
        {/* Leyenda */}
        {series.map((s, i) => (
          <g key={s.name}>
            <rect x={padding.left + i * 120} y={8} width={10} height={10} fill={colors[i % colors.length]} />
            <text x={padding.left + 14 + i * 120} y={17} fontSize={10}>{s.name}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}

export default function ForecastImportsPage() {
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState<'file' | 'url'>('file');
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [summary, setSummary] = useState<{ labels: string[]; series: { name: string; data: number[] }[] } | null>(null);
  const [range, setRange] = useState<{ from: string; to: string }>(() => {
    const today = new Date();
    const to = today.toISOString().slice(0, 10);
    const fromD = new Date(today.getTime() - 27 * 24 * 60 * 60 * 1000);
    const from = fromD.toISOString().slice(0, 10);
    return { from, to };
  });
  const [groupBy, setGroupBy] = useState<'location' | 'employee'>('location');

  const authHeaders = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const fetchSummary = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/imports/forecasts/summary`, {
        headers: authHeaders,
        params: { date_from: range.from, date_to: range.to, group_by: groupBy },
      });
      setSummary(res.data);
    } finally {
      setLoading(false);
    }
  };

  const handleFileImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post(`/imports/forecasts/file`, formData, {
        headers: { ...authHeaders, 'Content-Type': 'multipart/form-data' },
      });
      setResult(res.data);
      await fetchSummary();
    } catch (err: any) {
      setResult({ error: err?.response?.data?.detail || 'Error en importación' });
    } finally {
      setLoading(false);
    }
  };

  const handleUrlImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;
    setLoading(true);
    try {
      const res = await api.post(`/imports/forecasts/url`, null, {
        headers: authHeaders,
        params: { url },
      });
      setResult(res.data);
      await fetchSummary();
    } catch (err: any) {
      setResult({ error: err?.response?.data?.detail || 'Error en importación' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1>Importar Previsiones</h1>
        <div className="page-actions">
          <label>
            Desde
            <input type="date" value={range.from} onChange={(e) => setRange((r) => ({ ...r, from: e.target.value }))} />
          </label>
          <label>
            Hasta
            <input type="date" value={range.to} onChange={(e) => setRange((r) => ({ ...r, to: e.target.value }))} />
          </label>
          <select value={groupBy} onChange={(e) => setGroupBy(e.target.value as any)}>
            <option value="location">Por ubicación</option>
            <option value="employee">Por empleado</option>
          </select>
          <button onClick={fetchSummary} disabled={loading}>Actualizar gráfico</button>
        </div>
      </div>

      <div className="card">
        <div className="tabs">
          <button className={activeTab === 'file' ? 'active' : ''} onClick={() => setActiveTab('file')}>Subir archivo</button>
          <button className={activeTab === 'url' ? 'active' : ''} onClick={() => setActiveTab('url')}>Desde URL</button>
        </div>
        {activeTab === 'file' ? (
          <form onSubmit={handleFileImport} className="form-grid">
            <div>
              <input type="file" accept=".csv,.xlsx" onChange={(e) => setFile(e.target.files?.[0] || null)} />
              <div className="hint">
                Formato flexible: acepta CSV/XLSX con encabezados en español o inglés
                (ej: <code>fecha/date</code>, <code>correo/email</code>, <code>codigo_turno/shift_code</code>, <code>ubicacion/location</code>).
                Separadores CSV válidos: coma, punto y coma o tabulación.
              </div>
            </div>
            <div>
              <button type="submit" disabled={!file || loading}>{loading ? 'Importando...' : 'Importar'}</button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleUrlImport} className="form-grid">
            <input type="url" placeholder="https://... (CSV/XLSX)" value={url} onChange={(e) => setUrl(e.target.value)} />
            <button type="submit" disabled={!url || loading}>{loading ? 'Importando...' : 'Importar'}</button>
          </form>
        )}
      </div>

      {result && (
        <div className="card">
          <h3>Resultado</h3>
          {result.error ? (
            <div className="error">{result.error}</div>
          ) : (
            <div>
              <div>Filas OK: {result.result?.rows_ok} | Filas con error: {result.result?.rows_error}</div>
              {result.result?.errors?.length > 0 && (
                <details>
                  <summary>Ver errores</summary>
                  <ul>
                    {result.result.errors.map((e: any, i: number) => (
                      <li key={i}>Fila {e.row}: {e.error}</li>
                    ))}
                  </ul>
                </details>
              )}
              {result.sample && (
                <details>
                  <summary>Vista previa de filas</summary>
                  <pre>{JSON.stringify(result.sample, null, 2)}</pre>
                </details>
              )}
            </div>
          )}
        </div>
      )}

      <div className="card">
        <h3>Visualización tipo Manhattan</h3>
        {summary ? (
          <ManhattanChart labels={summary.labels} series={summary.series} />
        ) : (
          <div className="hint">Cargue datos y pulse "Actualizar gráfico"</div>
        )}
      </div>
    </div>
  );
}
