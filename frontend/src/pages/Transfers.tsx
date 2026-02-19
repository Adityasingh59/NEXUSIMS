import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { skusApi, type SKU } from '../api/skus';
import { transfersApi, type TransferOrder } from '../api/transfers';
import { warehousesApi, type Warehouse } from '../api/warehouses';

export function Transfers() {
  const [fromWarehouseId, setFromWarehouseId] = useState('');
  const [toWarehouseId, setToWarehouseId] = useState('');
  const [lines, setLines] = useState<Array<{ sku_id: string; quantity_requested: number }>>([{ sku_id: '', quantity_requested: 0 }]);
  const [showForm, setShowForm] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');

  const { data: whData } = useQuery({
    queryKey: ['warehouses'],
    queryFn: async () => { const r = await warehousesApi.list(); return r.data?.data ?? []; },
  });
  const { data: skusData } = useQuery({
    queryKey: ['skus'],
    queryFn: async () => { const r = await skusApi.list(); return r.data?.data ?? []; },
  });
  const { data: txData, refetch } = useQuery({
    queryKey: ['transfers', statusFilter],
    queryFn: async () => { const r = await transfersApi.list({ status: statusFilter || undefined }); return r.data?.data ?? []; },
  });

  const warehouses = (whData ?? []) as Warehouse[];
  const skus = (skusData ?? []) as SKU[];
  const transfers = (txData ?? []) as TransferOrder[];

  const addLine = () => setLines([...lines, { sku_id: '', quantity_requested: 0 }]);
  const removeLine = (i: number) => setLines(lines.filter((_, idx) => idx !== i));
  const updateLine = (i: number, key: 'sku_id' | 'quantity_requested', value: string | number) => {
    const next = [...lines];
    (next[i] as Record<string, unknown>)[key] = key === 'quantity_requested' ? Number(value) : value;
    setLines(next);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fromWarehouseId || !toWarehouseId || fromWarehouseId === toWarehouseId) return;
    const validLines = lines.filter(l => l.sku_id && l.quantity_requested > 0);
    if (validLines.length === 0) return;
    try {
      await transfersApi.create({
        from_warehouse_id: fromWarehouseId,
        to_warehouse_id: toWarehouseId,
        lines: validLines,
      });
      setLines([{ sku_id: '', quantity_requested: 0 }]);
      setShowForm(false);
      refetch();
    } catch (err) {
      console.error(err);
    }
  };

  const handleReceive = async (id: string) => {
    try {
      await transfersApi.receive(id);
      refetch();
    } catch (err) {
      console.error(err);
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await transfersApi.cancel(id);
      refetch();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="page transfers">
      <h1>Transfer Orders</h1>
      <p>Transfer stock between warehouses. TRANSFER_OUT on create, TRANSFER_IN on receive.</p>
      <button onClick={() => setShowForm(!showForm)}>{showForm ? 'Cancel' : '+ New Transfer'}</button>

      {showForm && (
        <form onSubmit={handleCreate} className="form">
          <h2>Create Transfer</h2>
          <label>From <select value={fromWarehouseId} onChange={e => setFromWarehouseId(e.target.value)} required>
            <option value="">Select...</option>
            {warehouses.map(w => <option key={w.id} value={w.id}>{w.code}</option>)}
          </select></label>
          <label>To <select value={toWarehouseId} onChange={e => setToWarehouseId(e.target.value)} required>
            <option value="">Select...</option>
            {warehouses.filter(w => w.id !== fromWarehouseId).map(w => <option key={w.id} value={w.id}>{w.code}</option>)}
          </select></label>
          <h3>Lines</h3>
          {lines.map((l, i) => (
            <div key={i} className="schema-row">
              <select value={l.sku_id} onChange={e => updateLine(i, 'sku_id', e.target.value)} required>
                <option value="">SKU...</option>
                {skus.map(s => <option key={s.id} value={s.id}>{s.sku_code}</option>)}
              </select>
              <input type="number" value={l.quantity_requested || ''} onChange={e => updateLine(i, 'quantity_requested', e.target.value)} placeholder="Qty" required min="0.01" step="0.01" />
              <button type="button" onClick={() => removeLine(i)}>Remove</button>
            </div>
          ))}
          <button type="button" onClick={addLine}>+ Add Line</button>
          <button type="submit">Create</button>
        </form>
      )}

      <div className="filters">
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="IN_TRANSIT">In transit</option>
          <option value="RECEIVED">Received</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
      </div>
      <table className="table">
        <thead>
          <tr><th>From</th><th>To</th><th>Status</th><th>Created</th><th>Actions</th></tr>
        </thead>
        <tbody>
          {transfers.map(t => (
            <tr key={t.id}>
              <td>{warehouses.find(w => w.id === t.from_warehouse_id)?.code ?? t.from_warehouse_id}</td>
              <td>{warehouses.find(w => w.id === t.to_warehouse_id)?.code ?? t.to_warehouse_id}</td>
              <td>{t.status}</td>
              <td>{t.created_at ? new Date(t.created_at).toLocaleString() : '-'}</td>
              <td>
                {t.status === 'IN_TRANSIT' && (
                  <>
                    <button type="button" onClick={() => handleReceive(t.id)}>Receive</button>
                    <button type="button" onClick={() => handleCancel(t.id)}>Cancel</button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
