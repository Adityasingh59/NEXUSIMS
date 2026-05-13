import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../lib/api';
import { useToast } from '../lib/toast';

interface Webhook {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
}

interface Delivery {
  id: string;
  event_type: string;
  status: string;
  response_status: number | null;
  attempt_count: number;
  last_attempt_at: string | null;
}

const ALL_EVENTS = [
  'RECEIVE', 'PICK', 'ADJUST', 'RETURN',
  'TRANSFER_OUT', 'TRANSFER_IN', 'COUNT_CORRECT',
  'WRITE_OFF', 'ASSEMBLE_OUT', 'ASSEMBLE_IN',
  'SHIP_OUT', 'RESERVE_OUT', 'RESERVE_IN',
];

export function Webhooks() {
  const toast = useToast();
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const [url, setUrl] = useState('');
  const [secret, setSecret] = useState('');
  const [events, setEvents] = useState<string[]>(['RECEIVE', 'PICK', 'SHIP_OUT']);

  const { data: webhooks = [], isLoading } = useQuery({
    queryKey: ['webhooks'],
    queryFn: () => apiClient.get('/webhooks/').then(r => r.data.data as Webhook[]),
  });

  const { data: deliveries = [] } = useQuery({
    queryKey: ['webhook-deliveries', selectedId],
    queryFn: () => selectedId
      ? apiClient.get(`/webhooks/${selectedId}/deliveries`).then(r => r.data.data as Delivery[])
      : Promise.resolve([] as Delivery[]),
    enabled: !!selectedId,
  });

  const createMutation = useMutation({
    mutationFn: (payload: unknown) => apiClient.post('/webhooks/', payload),
    onSuccess: () => { toast.success('Webhook created'); qc.invalidateQueries({ queryKey: ['webhooks'] }); resetForm(); },
    onError: () => toast.error('Failed to create webhook'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/webhooks/${id}`),
    onSuccess: () => { toast.success('Webhook deleted'); qc.invalidateQueries({ queryKey: ['webhooks'] }); setSelectedId(null); },
    onError: () => toast.error('Failed to delete webhook'),
  });

  const retryMutation = useMutation({
    mutationFn: ({ webhookId, deliveryId }: { webhookId: string; deliveryId: string }) =>
      apiClient.post(`/webhooks/${webhookId}/deliveries/${deliveryId}/retry`, {}),
    onSuccess: () => { toast.success('Retry enqueued'); qc.invalidateQueries({ queryKey: ['webhook-deliveries', selectedId] }); },
    onError: () => toast.error('Retry failed'),
  });

  const resetForm = () => { setUrl(''); setSecret(''); setEvents(['RECEIVE', 'PICK', 'SHIP_OUT']); setShowCreate(false); };

  const toggleEvent = (ev: string) =>
    setEvents(prev => prev.includes(ev) ? prev.filter(e => e !== ev) : [...prev, ev]);

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url || !secret) { toast.warning('URL and secret are required'); return; }
    createMutation.mutate({ url, secret, events, is_active: true });
  };

  const selectedWebhook = (webhooks as Webhook[]).find(w => w.id === selectedId);

  const statusColor = (status: string) => {
    if (status === 'SUCCESS') return 'var(--color-green)';
    if (status === 'FAILED') return 'var(--color-red)';
    return 'var(--color-amber)';
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1>Webhooks</h1>
        <p>Push real-time events to external URLs when stock transactions occur.</p>
        <div className="page-actions">
          <button onClick={() => { resetForm(); setShowCreate(true); }}>+ New Webhook</button>
        </div>
      </div>

      {showCreate && (
        <div className="modal-backdrop" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>New Webhook</h2>
              <button className="modal-close" onClick={() => setShowCreate(false)}>✕</button>
            </div>
            <form onSubmit={handleCreate}>
              <label>Endpoint URL
                <input type="url" value={url} onChange={e => setUrl(e.target.value)} required placeholder="https://your-server.com/hook" />
              </label>
              <label style={{ marginTop: '0.75rem', display: 'block' }}>Signing Secret
                <input value={secret} onChange={e => setSecret(e.target.value)} required placeholder="A strong random secret" />
              </label>
              <div style={{ marginTop: '0.75rem' }}>
                <div style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--color-mist)', marginBottom: '0.5rem' }}>Events to subscribe</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                  {ALL_EVENTS.map(ev => (
                    <label key={ev} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', cursor: 'pointer', fontSize: '0.78rem' }}>
                      <input type="checkbox" checked={events.includes(ev)} onChange={() => toggleEvent(ev)} />
                      {ev}
                    </label>
                  ))}
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="outline" onClick={() => setShowCreate(false)}>Cancel</button>
                <button type="submit" disabled={createMutation.isPending}>{createMutation.isPending ? 'Creating…' : 'Create Webhook'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {selectedId && selectedWebhook && (
        <div className="modal-backdrop" onClick={() => setSelectedId(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 700 }}>
            <div className="modal-header">
              <h2>Delivery Log — {selectedWebhook.url.slice(0, 40)}{selectedWebhook.url.length > 40 ? '…' : ''}</h2>
              <button className="modal-close" onClick={() => setSelectedId(null)}>✕</button>
            </div>
            {(deliveries as Delivery[]).length === 0 ? (
              <div className="empty-state"><h3>No deliveries yet</h3></div>
            ) : (
              <table className="table" style={{ marginTop: '0.5rem' }}>
                <thead><tr><th>Event</th><th>Status</th><th>HTTP</th><th>Attempts</th><th>Last Attempt</th><th></th></tr></thead>
                <tbody>
                  {(deliveries as Delivery[]).map(d => (
                    <tr key={d.id}>
                      <td><span className="badge badge-info">{d.event_type}</span></td>
                      <td><span style={{ color: statusColor(d.status), fontWeight: 600, fontSize: '0.8rem' }}>{d.status}</span></td>
                      <td>{d.response_status ?? '—'}</td>
                      <td>{d.attempt_count}</td>
                      <td className="text-muted">{d.last_attempt_at ? new Date(d.last_attempt_at).toLocaleString() : '—'}</td>
                      <td>
                        {d.status === 'FAILED' && (
                          <button className="btn-sm warning" onClick={() => retryMutation.mutate({ webhookId: selectedId, deliveryId: d.id })}>
                            Retry
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="loading">Loading webhooks</div>
      ) : (webhooks as Webhook[]).length === 0 ? (
        <div className="empty-state card">
          <h3>No webhooks configured</h3>
          <p>Create a webhook to push events to external services.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Endpoint URL</th><th>Events</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead>
            <tbody>
              {(webhooks as Webhook[]).map(wh => (
                <tr key={wh.id}>
                  <td className="mono" style={{ fontSize: '0.8rem' }}>{wh.url}</td>
                  <td>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                      {(wh.events ?? []).slice(0, 4).map(ev => <span key={ev} className="badge badge-info" style={{ fontSize: '0.65rem' }}>{ev}</span>)}
                      {(wh.events ?? []).length > 4 && <span className="badge" style={{ fontSize: '0.65rem' }}>+{wh.events.length - 4}</span>}
                    </div>
                  </td>
                  <td><span className={`badge ${wh.is_active ? 'badge-received' : 'badge-inactive'}`}>{wh.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td className="text-muted">{wh.created_at ? new Date(wh.created_at).toLocaleDateString() : '—'}</td>
                  <td style={{ display: 'flex', gap: '0.4rem' }}>
                    <button className="btn-sm secondary" onClick={() => setSelectedId(wh.id)}>Deliveries</button>
                    <button className="btn-sm btn-danger"
                      onClick={() => { if (window.confirm('Delete this webhook?')) deleteMutation.mutate(wh.id); }}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
