import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { webhooksApi } from '../api/webhooks';
import type { Webhook } from '../api/webhooks';

export function Webhooks() {
    const queryClient = useQueryClient();
    const [showForm, setShowForm] = useState(false);
    const [url, setUrl] = useState('');
    const [secret, setSecret] = useState('');
    const [events, setEvents] = useState('PO_RECEIVED, PO_PARTIAL, RECEIVE, PICK, ADJUST');
    const [selectedWebhook, setSelectedWebhook] = useState<string | null>(null);

    const { data: webhooks, isLoading } = useQuery({
        queryKey: ['webhooks'],
        queryFn: () => webhooksApi.list().then(r => r.data.data),
    });

    const { data: deliveries } = useQuery({
        queryKey: ['webhook-deliveries', selectedWebhook],
        queryFn: () => selectedWebhook ? webhooksApi.listDeliveries(selectedWebhook).then(r => r.data.data) : null,
        enabled: !!selectedWebhook,
    });

    const createMutation = useMutation({
        mutationFn: (data: Partial<Webhook>) => webhooksApi.create(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['webhooks'] });
            setShowForm(false);
            setUrl('');
            setSecret('');
        }
    });

    const deleteMutation = useMutation({
        mutationFn: (id: string) => webhooksApi.delete(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['webhooks'] });
            if (selectedWebhook) setSelectedWebhook(null);
        }
    });

    const retryMutation = useMutation({
        mutationFn: (d: { w_id: string, d_id: string }) => webhooksApi.retryDelivery(d.w_id, d.d_id),
        onSuccess: () => {
            alert("Retry enqueued");
            queryClient.invalidateQueries({ queryKey: ['webhook-deliveries'] });
        }
    });

    const handleCreate = (e: React.FormEvent) => {
        e.preventDefault();
        createMutation.mutate({
            url,
            events: events.split(',').map(s => s.trim()).filter(Boolean),
            is_active: true
        });
    };

    if (isLoading) return <div className="loading">Loading...</div>;

    return (
        <div className="page webhooks">
            <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1>Webhooks</h1>
                    <p>Subscribe to inventory events</p>
                </div>
                <button className="btn-primary" onClick={() => setShowForm(!showForm)}>
                    {showForm ? 'Cancel' : '+ New Webhook'}
                </button>
            </div>

            {showForm && (
                <form className="card form" onSubmit={handleCreate} style={{ marginBottom: '2rem' }}>
                    <h3>Create Webhook</h3>
                    <div className="form-group">
                        <label>Payload URL</label>
                        <input type="url" required value={url} onChange={e => setUrl(e.target.value)} placeholder="https://example.com/webhook" />
                    </div>
                    <div className="form-group">
                        <label>Secret</label>
                        <input type="text" required value={secret} onChange={e => setSecret(e.target.value)} placeholder="Secret for HMAC signature" />
                    </div>
                    <div className="form-group">
                        <label>Events (comma separated, use * for all)</label>
                        <input type="text" required value={events} onChange={e => setEvents(e.target.value)} />
                    </div>
                    <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
                        {createMutation.isPending ? 'Saving...' : 'Save Webhook'}
                    </button>
                </form>
            )}

            <div className="card">
                <table className="table">
                    <thead>
                        <tr>
                            <th>URL</th>
                            <th>Events</th>
                            <th>Status</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {(webhooks || []).map(w => (
                            <tr key={w.id}>
                                <td>{w.url}</td>
                                <td>{w.events.join(', ')}</td>
                                <td>
                                    <span className={`badge ${w.is_active ? 'badge-success' : 'badge-danger'}`}>
                                        {w.is_active ? 'Active' : 'Disabled'}
                                    </span>
                                </td>
                                <td>{new Date(w.created_at).toLocaleDateString()}</td>
                                <td>
                                    <button className="btn-ghost text-xs cursor-pointer" onClick={() => setSelectedWebhook(w.id)}>View Deliveries</button>
                                    <button className="btn-danger text-xs cursor-pointer" style={{ marginLeft: '0.5rem' }} onClick={() => confirm('Delete?') && deleteMutation.mutate(w.id)}>Delete</button>
                                </td>
                            </tr>
                        ))}
                        {(webhooks || []).length === 0 && (
                            <tr><td colSpan={5} style={{ textAlign: 'center', opacity: 0.5 }}>No webhooks configured</td></tr>
                        )}
                    </tbody>
                </table>
            </div>

            {selectedWebhook && (
                <div className="card" style={{ marginTop: '2rem' }}>
                    <h3>Recent Deliveries</h3>
                    <table className="table">
                        <thead>
                            <tr>
                                <th>Event Type</th>
                                <th>Status</th>
                                <th>Attempts</th>
                                <th>Last Attempt</th>
                                <th>Response</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {(deliveries || []).map(d => (
                                <tr key={d.id}>
                                    <td>{d.event_type}</td>
                                    <td>
                                        <span className={`badge ${d.status === 'SUCCESS' ? 'badge-success' : d.status === 'FAILED' ? 'badge-danger' : 'badge-warning'}`}>
                                            {d.status}
                                        </span>
                                    </td>
                                    <td>{d.attempts}</td>
                                    <td>{d.last_attempt_at ? new Date(d.last_attempt_at).toLocaleString() : '—'}</td>
                                    <td>{d.response_code || '—'}</td>
                                    <td>
                                        {d.status === 'FAILED' && (
                                            <button className="btn-primary text-xs cursor-pointer" onClick={() => retryMutation.mutate({ w_id: selectedWebhook, d_id: d.id })}>
                                                Retry
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                            {(deliveries || []).length === 0 && (
                                <tr><td colSpan={6} style={{ textAlign: 'center', opacity: 0.5 }}>No deliveries yet</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
