import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { rmaApi } from '../api/rma';
import type { RMA } from '../api/rma';

export function Returns() {
    const queryClient = useQueryClient();
    const [selectedRma, setSelectedRma] = useState<RMA | null>(null);

    const { data: rmas, isLoading } = useQuery({
        queryKey: ['rmas'],
        queryFn: () => rmaApi.list().then(r => r.data.data),
    });

    const updateStatusMutation = useMutation({
        mutationFn: (d: { id: string, status: string }) => rmaApi.updateStatus(d.id, d.status),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['rmas'] });
            setSelectedRma(null);
        }
    });

    const receiveMutation = useMutation({
        mutationFn: (d: { id: string, lines: any[] }) => rmaApi.receive(d.id, d.lines),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['rmas'] });
            setSelectedRma(null);
        }
    });

    if (isLoading) return <div className="loading">Loading Returns...</div>;

    return (
        <div className="page returns">
            <div className="page-header">
                <div>
                    <h1>Returns (RMA)</h1>
                    <p>Manage customer returns and reverse logistics</p>
                </div>
            </div>

            <div className="card">
                <table className="table">
                    <thead>
                        <tr>
                            <th>RMA ID</th>
                            <th>Customer</th>
                            <th>Status</th>
                            <th>Created Date</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {(rmas || []).map(rma => (
                            <tr key={rma.id}>
                                <td>{rma.id.split('-')[0]}</td>
                                <td>{rma.customer_name || '—'}</td>
                                <td>
                                    <span className={`badge ${['APPROVED', 'RESTOCKED'].includes(rma.status) ? 'badge-success' : rma.status === 'REJECTED' ? 'badge-danger' : 'badge-warning'}`}>
                                        {rma.status}
                                    </span>
                                </td>
                                <td>{new Date(rma.created_at).toLocaleDateString()}</td>
                                <td>
                                    <button className="btn-ghost text-xs" onClick={() => setSelectedRma(rma)}>Manage</button>
                                </td>
                            </tr>
                        ))}
                        {(rmas || []).length === 0 && (
                            <tr><td colSpan={5} style={{ textAlign: 'center', opacity: 0.5 }}>No returns found</td></tr>
                        )}
                    </tbody>
                </table>
            </div>

            {selectedRma && (
                <div className="card" style={{ marginTop: '2rem' }}>
                    <h3>Manage RMA: {selectedRma.id.split('-')[0]}</h3>
                    <table className="table">
                        <thead>
                            <tr>
                                <th>SKU ID</th>
                                <th>Expected</th>
                                <th>Received</th>
                                <th>Condition</th>
                            </tr>
                        </thead>
                        <tbody>
                            {selectedRma.lines.map(line => (
                                <tr key={line.id}>
                                    <td>{line.sku_id.split('-')[0]}</td>
                                    <td>{line.quantity_expected}</td>
                                    <td>{line.quantity_received}</td>
                                    <td>{line.condition || '—'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem' }}>
                        {selectedRma.status === 'PENDING' && (
                            <button
                                className="btn-primary"
                                onClick={() => {
                                    const linesToReceive = selectedRma.lines.map(l => ({ rma_line_id: l.id, quantity: l.quantity_expected }));
                                    receiveMutation.mutate({ id: selectedRma.id, lines: linesToReceive });
                                }}
                            >
                                Receive All Items into Quarantine
                            </button>
                        )}

                        {selectedRma.status === 'INSPECTING' && (
                            <>
                                <button className="btn-success" onClick={() => updateStatusMutation.mutate({ id: selectedRma.id, status: 'APPROVED' })}>Approve Return</button>
                                <button className="btn-danger" onClick={() => updateStatusMutation.mutate({ id: selectedRma.id, status: 'REJECTED' })}>Reject Return</button>
                            </>
                        )}

                        {selectedRma.status === 'APPROVED' && (
                            <button className="btn-primary" onClick={() => updateStatusMutation.mutate({ id: selectedRma.id, status: 'RESTOCKED' })}>Route to Stock Location</button>
                        )}

                        <button className="btn-ghost" onClick={() => setSelectedRma(null)}>Cancel</button>
                    </div>
                </div>
            )}
        </div>
    );
}
