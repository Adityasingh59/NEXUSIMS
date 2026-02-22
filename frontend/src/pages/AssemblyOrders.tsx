import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { getAssemblyOrders, createAssemblyOrder, completeAssemblyOrder, cancelAssemblyOrder, getBOMs } from '../api/assembly';
import { warehousesApi, type Warehouse } from '../api/warehouses';
import { skusApi, type SKU } from '../api/skus';

export function AssemblyOrders() {
    const queryClient = useQueryClient();
    const [showCreate, setShowCreate] = useState(false);
    const [statusFilter, setStatusFilter] = useState('');

    // Start Order Form
    const [formBomId, setFormBomId] = useState('');
    const [formWarehouseId, setFormWarehouseId] = useState('');
    const [formPlannedQty, setFormPlannedQty] = useState<number>(1);

    // Complete Order Form
    const [completingOrderId, setCompletingOrderId] = useState<string | null>(null);
    const [formProducedQty, setFormProducedQty] = useState<number>(0);
    const [formWasteQty, setFormWasteQty] = useState<number>(0);
    const [formWasteReason, setFormWasteReason] = useState<string>('');

    const { data: ordersData, isLoading: ordersLoading } = useQuery({
        queryKey: ['assembly-orders', statusFilter],
        queryFn: async () => await getAssemblyOrders(statusFilter ? { status: statusFilter } : {}),
    });

    const { data: bomsData } = useQuery({
        queryKey: ['boms-active'],
        queryFn: async () => await getBOMs({ include_inactive: false }),
    });

    const { data: warehousesData } = useQuery({
        queryKey: ['warehouses'],
        queryFn: async () => { const r = await warehousesApi.list(); return r.data?.data ?? []; },
    });

    const { data: skusData } = useQuery({
        queryKey: ['skus'],
        queryFn: async () => { const r = await skusApi.list(); return r.data?.data ?? []; },
    });

    const orders = ordersData?.data ?? [];
    const boms = bomsData?.data ?? [];
    const warehouses = (warehousesData ?? []) as Warehouse[];
    const skus = (skusData ?? []) as SKU[];

    const startMutation = useMutation({
        mutationFn: createAssemblyOrder,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['assembly-orders'] });
            setShowCreate(false);
            setFormBomId('');
            setFormWarehouseId('');
            setFormPlannedQty(1);
        },
        onError: (err: any) => {
            console.error("Failed to start order", err);
            const msg = err?.response?.data?.detail;
            if (typeof msg === 'string') alert(`Error: ${msg}`);
            else if (Array.isArray(msg)) alert(`Validation Error: ${JSON.stringify(msg)}`);
            else alert("Error starting order. Check component availability.");
        }
    });

    const completeMutation = useMutation({
        mutationFn: (data: { id: string, payload: any }) => completeAssemblyOrder(data.id, data.payload),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['assembly-orders'] });
            setCompletingOrderId(null);
        },
        onError: (err) => {
            console.error(err);
            alert("Error completing order");
        }
    });

    const cancelMutation = useMutation({
        mutationFn: cancelAssemblyOrder,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['assembly-orders'] });
        },
        onError: (err) => {
            console.error(err);
            alert("Error cancelling order");
        }
    });

    const handleStartSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!formBomId || !formWarehouseId || formPlannedQty <= 0) return;
        startMutation.mutate({
            bom_id: formBomId,
            warehouse_id: formWarehouseId,
            planned_qty: formPlannedQty
        });
    };

    const handleCompleteSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!completingOrderId) return;
        completeMutation.mutate({
            id: completingOrderId,
            payload: {
                produced_qty: formProducedQty,
                waste_qty: formWasteQty || 0,
                waste_reason: formWasteReason || null
            }
        });
    };

    const skuDetails = (finishedSkuId: string) => {
        const sku = skus.find(s => s.id === finishedSkuId);
        if (!sku) return 'Unknown SKU';
        return `${sku.sku_code} - ${sku.name}`;
    };

    const bomNameFor = (bomId: string) => {
        const matchingBom = boms.find(b => b.id === bomId);
        if (!matchingBom) return 'BOM Details Unknown...';
        return `v${matchingBom.version} (${skuDetails(matchingBom.finished_sku_id)})`;
    };

    const warehouseName = (id: string) => warehouses.find(w => w.id === id)?.name ?? 'Unknown';

    return (
        <div className="page assembly-orders">
            <h1>Assembly Orders</h1>
            <p>Manage the production lifecycle: reserve components, execute assembly, and register finished goods.</p>

            <div className="filters" style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap' }}>
                <button onClick={() => setShowCreate(true)} className="btn primary">+ Start New Order</button>
                <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                    <option value="">All Statuses</option>
                    <option value="PENDING">Pending</option>
                    <option value="IN_PROGRESS">In Progress</option>
                    <option value="COMPLETE">Complete</option>
                    <option value="CANCELLED">Cancelled</option>
                </select>
            </div>

            {showCreate && (
                <form onSubmit={handleStartSubmit} className="form" style={{ marginBottom: '2rem', padding: '1.5rem', background: 'var(--color-surface)', borderRadius: '8px', border: '1px solid var(--color-edge)' }}>
                    <h2 style={{ marginTop: 0 }}>Start Assembly Order</h2>
                    <p style={{ fontSize: '0.9rem', color: 'var(--color-white)', opacity: 0.8 }}>Starting an order will immediately reserve (deduct) the required components from stock.</p>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
                        <div>
                            <label>Recipe (Active BOM)</label>
                            <select value={formBomId} onChange={e => setFormBomId(e.target.value)} required>
                                <option value="">Select BOM...</option>
                                {boms.map(b => (
                                    <option key={b.id} value={b.id}>
                                        {skuDetails(b.finished_sku_id)} [v{b.version}]
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label>Warehouse (Execution Location)</label>
                            <select value={formWarehouseId} onChange={e => setFormWarehouseId(e.target.value)} required>
                                <option value="">Select Warehouse...</option>
                                {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                            </select>
                        </div>
                        <div>
                            <label>Planned Quantity</label>
                            <input type="number" step="0.0001" min="0.0001" value={formPlannedQty} onChange={e => setFormPlannedQty(Number(e.target.value))} required />
                        </div>
                    </div>

                    <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem' }}>
                        <button type="submit" className="btn primary" disabled={startMutation.isPending}>
                            {startMutation.isPending ? 'Starting...' : 'Start Production'}
                        </button>
                        <button type="button" onClick={() => setShowCreate(false)} className="btn text">Cancel</button>
                    </div>
                </form>
            )}

            {completingOrderId && (
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
                    <form onSubmit={handleCompleteSubmit} className="form modal" style={{ background: 'var(--color-ink)', padding: '2rem', borderRadius: '8px', minWidth: '400px', boxShadow: '0 4px 20px rgba(0,0,0,0.15)' }}>
                        <h2 style={{ marginTop: 0 }}>Complete Assembly</h2>
                        <p style={{ opacity: 0.8, fontSize: '0.9rem' }}>Registering finished goods into stock. Enter actual yield and waste.</p>

                        <label>Produced Quantity (Yield)</label>
                        <input type="number" step="0.0001" min="0" value={formProducedQty} onChange={e => setFormProducedQty(Number(e.target.value))} required />

                        <label>Waste Quantity (Optional)</label>
                        <input type="number" step="0.0001" min="0" value={formWasteQty} onChange={e => setFormWasteQty(Number(e.target.value))} />

                        <label>Waste Reason</label>
                        <input type="text" placeholder="e.g. Scratched during assembly" value={formWasteReason} onChange={e => setFormWasteReason(e.target.value)} />

                        <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem' }}>
                            <button type="submit" className="btn primary" disabled={completeMutation.isPending}>
                                {completeMutation.isPending ? 'Completing...' : 'Complete Order'}
                            </button>
                            <button type="button" onClick={() => setCompletingOrderId(null)} className="btn text">Cancel</button>
                        </div>
                    </form>
                </div>
            )}

            <div className="table-container">
                {ordersLoading ? (
                    <p>Loading Orders...</p>
                ) : (
                    <table>
                        <thead>
                            <tr>
                                <th>Order ID</th>
                                <th>Target BOM</th>
                                <th>Warehouse</th>
                                <th>Status</th>
                                <th>Planned</th>
                                <th>Actual</th>
                                <th>COGS / Unit</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {orders.map(order => (
                                <tr key={order.id} style={{ opacity: order.status === 'CANCELLED' ? 0.6 : 1 }}>
                                    <td><small style={{ fontFamily: 'monospace' }}>{order.id.slice(0, 8)}</small></td>
                                    <td>
                                        <strong>{bomNameFor(order.bom_id)}</strong>
                                    </td>
                                    <td>{warehouseName(order.warehouse_id)}</td>
                                    <td>
                                        <span style={{
                                            padding: '4px 8px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 600,
                                            background: order.status === 'COMPLETE' ? '#e8f5e9' :
                                                order.status === 'IN_PROGRESS' ? '#fff3e0' :
                                                    order.status === 'CANCELLED' ? '#ffebee' : '#f5f5f5',
                                            color: order.status === 'COMPLETE' ? '#2e7d32' :
                                                order.status === 'IN_PROGRESS' ? '#ef6c00' :
                                                    order.status === 'CANCELLED' ? '#c62828' : '#424242',
                                        }}>
                                            {order.status}
                                        </span>
                                    </td>
                                    <td>{Number(order.planned_qty)}</td>
                                    <td>{order.produced_qty ? Number(order.produced_qty) : '-'}</td>
                                    <td>{order.cogs_per_unit ? `$${Number(order.cogs_per_unit).toFixed(2)}` : '-'}</td>
                                    <td>
                                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                                            {order.status === 'IN_PROGRESS' && (
                                                <>
                                                    <button onClick={() => {
                                                        setFormProducedQty(Number(order.planned_qty));
                                                        setFormWasteQty(0);
                                                        setFormWasteReason('');
                                                        setCompletingOrderId(order.id);
                                                    }} className="btn primary sm">Complete</button>
                                                    <button onClick={() => {
                                                        if (window.confirm("Cancel this order? This will not return reserved components automatically.")) {
                                                            cancelMutation.mutate(order.id);
                                                        }
                                                    }} className="btn danger sm">Cancel</button>
                                                </>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {orders.length === 0 && (
                                <tr><td colSpan={8} style={{ textAlign: 'center', padding: '2rem' }}>No Assembly Orders found.</td></tr>
                            )}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}
