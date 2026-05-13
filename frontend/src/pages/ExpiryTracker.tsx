import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../lib/api';

interface ExpiredSKU {
  id: string;
  sku_code: string;
  name: string;
  expiry_date: string;
}

function daysDiff(dateStr: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const exp = new Date(dateStr);
  exp.setHours(0, 0, 0, 0);
  return Math.floor((exp.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

function urgency(dateStr: string) {
  const d = daysDiff(dateStr);
  if (d < 0) return { label: 'Expired', cls: 'badge-danger', days: `${Math.abs(d)}d ago` };
  if (d === 0) return { label: 'Today', cls: 'badge-danger', days: 'Today' };
  if (d <= 7) return { label: 'Critical', cls: 'badge-danger', days: `${d}d left` };
  if (d <= 30) return { label: 'Warning', cls: 'badge-warning', days: `${d}d left` };
  return { label: 'OK', cls: 'badge-received', days: `${d}d left` };
}

export function ExpiryTracker() {
  const { data: expired = [], isLoading, isError } = useQuery({
    queryKey: ['expiry-tracker'],
    queryFn: () => apiClient.get('/modules/expiry-tracker/expired').then(r => r.data as ExpiredSKU[]),
  });

  const expiredList = expired as ExpiredSKU[];

  return (
    <div className="page">
      <div className="page-header">
        <h1>Expiry Tracker</h1>
        <p>SKUs where <code>attributes.expiry_date</code> has passed. Requires the <strong>expiry-tracker</strong> module installed.</p>
      </div>

      {isLoading ? (
        <div className="loading">Loading expiry data</div>
      ) : isError ? (
        <div className="empty-state card" style={{ color: 'var(--color-red)' }}>
          <h3>Module not active</h3>
          <p>The <strong>expiry-tracker</strong> module must be installed and active for this tenant.</p>
        </div>
      ) : expiredList.length === 0 ? (
        <div className="empty-state card">
          <h3>No expired SKUs</h3>
          <p>All SKUs with an <code>expiry_date</code> attribute are within their validity period.</p>
        </div>
      ) : (
        <>
          <div className="kpi-grid" style={{ marginBottom: '1.5rem' }}>
            <div className="kpi-card">
              <div className="kpi-label">Total Expired / Expiring</div>
              <div className="kpi-value">{expiredList.length}</div>
              <div className="kpi-sub" style={{ color: 'var(--color-red)' }}>Needs attention</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Expired (past date)</div>
              <div className="kpi-value">{expiredList.filter(s => daysDiff(s.expiry_date) <= 0).length}</div>
              <div className="kpi-sub" style={{ color: 'var(--color-amber)' }}>Write-off candidates</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Expiring Within 7 Days</div>
              <div className="kpi-value">{expiredList.filter(s => { const d = daysDiff(s.expiry_date); return d > 0 && d <= 7; }).length}</div>
              <div className="kpi-sub" style={{ color: 'var(--color-amber)' }}>Critical window</div>
            </div>
          </div>

          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>SKU Code</th><th>Name</th><th>Expiry Date</th><th>Status</th><th>Days</th></tr>
              </thead>
              <tbody>
                {expiredList.map(s => {
                  const u = urgency(s.expiry_date);
                  return (
                    <tr key={s.id}>
                      <td><strong className="mono">{s.sku_code}</strong></td>
                      <td>{s.name}</td>
                      <td>{new Date(s.expiry_date).toLocaleDateString()}</td>
                      <td><span className={`badge ${u.cls}`}>{u.label}</span></td>
                      <td className="mono" style={{ color: daysDiff(s.expiry_date) <= 0 ? 'var(--color-red)' : 'var(--color-amber)' }}>
                        {u.days}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
