import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { purchaseOrdersApi, type PurchaseOrder } from '../api/purchaseOrders';
import { skusApi, type SKU } from '../api/skus';
import { warehousesApi, type Warehouse } from '../api/warehouses';

type POLineForm = { sku_id: string; quantity_ordered: number; unit_cost: number };

const STATUS_COLORS: Record<string, string> = {
    DRAFT: '#888',
    ORDERED: '#2563eb',
    PARTIAL: '#d97706',
    RECEIVED: '#16a34a',
    CANCELLED: '#dc2626',
};

export function PurchaseOrders() {
    const [showCreate, setShowCreate] = useState(false);
    const [receivingPo, setReceivingPo] = useState<PurchaseOrder | null>(null);
    const [receiveQtys, setReceiveQtys] = useState<Record<string, number>>({});
    const [statusFilter, setStatusFilter] = useState('');

    // Create form state
    const [supplier, setSupplier] = useState('');
    const [warehouseId, setWarehouseId] = useState('');
    const [notes, setNotes] = useState('');
    const [poLines, setPoLines] = useState<POLineForm[]>([{ sku_id: '', quantity_ordered: 1, unit_cost: 0 }]);

    const { data: poData, refetch } = useQuery({
        queryKey: ['purchase-orders', statusFilter],
        queryFn: async () => {
            const r = await purchaseOrdersApi.list({ status: statusFilter || undefined });
            return r.data?.data ?? [];
        },
    });
    const { data: skusData } = useQuery({
        queryKey: ['skus'],
        queryFn: async () => { const r = await skusApi.list(); return r.data?.data ?? []; },
    });
    const { data: whData } = useQuery({
        queryKey: ['warehouses'],
        queryFn: async () => { const r = await warehousesApi.list(); return r.data?.data ?? []; },
    });

    const pos = (poData ?? []) as PurchaseOrder[];
    const skus = (skusData ?? []) as SKU[];
    const warehouses = (whData ?? []) as Warehouse[];

    const resetCreate = () => {
        setSupplier(''); setWarehouseId(''); setNotes('');
        setPoLines([{ sku_id: '', quantity_ordered: 1, unit_cost: 0 }]);
        setShowCreate(false);
    };

    const addPoLine = () => setPoLines([...poLines, { sku_id: '', quantity_ordered: 1, unit_cost: 0 }]);
    const removePoLine = (i: number) => setPoLines(poLines.filter((_, idx) => idx !== i));
    const updatePoLine = (i: number, key: keyof POLineForm, value: string | number) => {
        const next = [...poLines];
        (next[i] as Record<string, unknown>)[key] = key === 'sku_id' ? value : Number(value);
        setPoLines(next);
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        const validLines = poLines.filter(l => l.sku_id && l.quantity_ordered > 0);
        if (validLines.length === 0 || !warehouseId) return;
        try {
            await purchaseOrdersApi.create({ supplier_name: supplier, warehouse_id: warehouseId, notes: notes || undefined, lines: validLines });
            resetCreate();
            refetch();
        } catch (err) { console.error(err); }
    };

    const openReceive = (po: PurchaseOrder) => {
        setReceivingPo(po);
        const initial: Record<string, number> = {};
        po.lines.forEach(l => { initial[l.id] = 0; });
        setReceiveQtys(initial);
    };

    const handleReceive = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!receivingPo) return;
        const lines = Object.entries(receiveQtys)
            .filter(([, qty]) => qty > 0)
            .map(([po_line_id, quantity_received]) => ({ po_line_id, quantity_received }));
        if (lines.length === 0) return;
        try {
            await purchaseOrdersApi.receive(receivingPo.id, lines);
            setReceivingPo(null);
            refetch();
        } catch (err) { console.error(err); }
    };

    const handleCancel = async (id: string) => {
        if (!window.confirm('Cancel this Purchase Order?')) return;
        try { await purchaseOrdersApi.cancel(id); refetch(); } catch (err) { console.error(err); }
    };

    const skuCode = (id: string) => skus.find(s => s.id === id)?.sku_code ?? id.slice(0, 8) + '…';
    const whCode = (id: string) => warehouses.find(w => w.id === id)?.code ?? id.slice(0, 8) + '…';

    return (
        <div className="page purchase-orders">
            <h1>Purchase Orders</h1>
            <p>Manage inbound procurement. Receiving a PO automatically posts RECEIVE stock ledger events.</p>

            <div className="filters" style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem' }}>
                <button onClick={() => { resetCreate(); setShowCreate(true); }}>+ New PO</button>
                <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                    <option value="">All statuses</option>
                    <option value="DRAFT">Draft</option>
                    <option value="ORDERED">Ordered</option>
                    <option value="PARTIAL">Partial</option>
                    <option value="RECEIVED">Received</option>
                    <option value="CANCELLED">Cancelled</option>
                </select>
            </div>

            {showCreate && (
                <form onSubmit={handleCreate} className="form">
                    <h2>New Purchase Order</h2>
                    <label>Supplier Name
                        <input value={supplier} onChange={e => setSupplier(e.target.value)} required maxLength={255} placeholder="Supplier Co." />
                    </label>
                    <label>Receiving Warehouse
                        <select value={warehouseId} onChange={e => setWarehouseId(e.target.value)} required>
                            <option value="">Select warehouse…</option>
                            {warehouses.map(w => <option key={w.id} value={w.id}>{w.code} — {w.name}</option>)}
                        </select>
                    </label>
                    <label>Notes (optional)
                        <input value={notes} onChange={e => setNotes(e.target.value)} placeholder="e.g. Q1 restock" />
                    </label>
                    <h3>Line Items</h3>
                    {poLines.map((line, i) => (
                        <div key={i} className="schema-row">
                            <select value={line.sku_id} onChange={e => updatePoLine(i, 'sku_id', e.target.value)} required>
                                <option value="">SKU…</option>
                                {skus.map(s => <option key={s.id} value={s.id}>{s.sku_code}</option>)}
                            </select>
                            <input type="number" value={line.quantity_ordered || ''} onChange={e => updatePoLine(i, 'quantity_ordered', e.target.value)} placeholder="Qty" required min="0.0001" step="0.0001" style={{ width: '90px' }} />
                            <input type="number" value={line.unit_cost || ''} onChange={e => updatePoLine(i, 'unit_cost', e.target.value)} placeholder="Unit cost ($)" required min="0" step="0.01" style={{ width: '120px' }} />
                            <button type="button" onClick={() => removePoLine(i)} disabled={poLines.length === 1}>Remove</button>
                        </div>
                    ))}
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                        <button type="button" onClick={addPoLine}>+ Add Line</button>
                        <button type="submit">Create PO</button>
                        <button type="button" onClick={resetCreate}>Cancel</button>
                    </div>
                </form>
            )}

            {receivingPo && (
                <form onSubmit={handleReceive} className="form" style={{ marginTop: '1rem' }}>
                    <h2>Receive PO: {receivingPo.supplier_name}</h2>
                    <p>Enter the quantity received for each line (leave 0 to skip a line).</p>
                    <table className="table">
                        <thead>
                            <tr><th>SKU</th><th>Ordered</th><th>Already Received</th><th>Remaining</th><th>Receiving Now</th></tr>
                        </thead>
                        <tbody>
                            {receivingPo.lines.map(line => {
                                const remaining = Number(line.quantity_ordered) - Number(line.quantity_received);
                                return (
                                    <tr key={line.id}>
                                        <td>{skuCode(line.sku_id)}</td>
                                        <td>{Number(line.quantity_ordered).toFixed(2)}</td>
                                        <td>{Number(line.quantity_received).toFixed(2)}</td>
                                        <td>{remaining.toFixed(2)}</td>
                                        <td>
                                            <input
                                                type="number"
                                                min="0"
                                                max={remaining}
                                                step="0.0001"
                                                value={receiveQtys[line.id] ?? 0}
                                                onChange={e => setReceiveQtys({ ...receiveQtys, [line.id]: Number(e.target.value) })}
                                                style={{ width: '100px' }}
                                                disabled={remaining <= 0}
                                            />
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                        <button type="submit">Confirm Receipt</button>
                        <button type="button" onClick={() => setReceivingPo(null)}>Cancel</button>
                    </div>
                </form>
            )}

            <table className="table" style={{ marginTop: '1rem' }}>
                <thead>
                    <tr>
                        <th>Supplier</th>
                        <th>Warehouse</th>
                        <th>Status</th>
                        <th>Lines</th>
                        <th>Created</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {pos.map(po => (
                        <tr key={po.id}>
                            <td>{po.supplier_name}</td>
                            <td>{whCode(po.warehouse_id)}</td>
                            <td>
                                <span style={{ color: STATUS_COLORS[po.status] ?? '#888', fontWeight: 600 }}>
                                    {po.status}
                                </span>
                            </td>
                            <td>{po.lines.length} line{po.lines.length !== 1 ? 's' : ''}</td>
                            <td>{po.created_at ? new Date(po.created_at).toLocaleDateString() : '—'}</td>
                            <td>
                                {(po.status === 'DRAFT' || po.status === 'ORDERED' || po.status === 'PARTIAL') && (
                                    <button type="button" onClick={() => openReceive(po)} style={{ marginRight: '0.25rem' }}>Receive</button>
                                )}
                                {(po.status === 'DRAFT' || po.status === 'ORDERED') && (
                                    <button type="button" onClick={() => handleCancel(po.id)}>Cancel</button>
                                )}
                            </td>
                        </tr>
                    ))}
                    {pos.length === 0 && (
                        <tr><td colSpan={6} style={{ textAlign: 'center', color: '#888' }}>No purchase orders found.</td></tr>
                    )}
                </tbody>
            </table>
        </div>
    );
}
