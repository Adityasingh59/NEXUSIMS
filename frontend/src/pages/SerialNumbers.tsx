import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../lib/api';
import { skusApi } from '../api/skus';
import { warehousesApi } from '../api/warehouses';
import { useToast } from '../lib/toast';
import type { SKU } from '../api/skus';
import type { Warehouse } from '../api/warehouses';

interface SerialNumber {
  id: string;
  sku_id: string;
  warehouse_id: string;
  serial_number: string;
  status: string;
}

const STATUSES = ['IN_STOCK', 'SOLD', 'RETURNED', 'DEFECTIVE', 'QUARANTINE'];
const STATUS_COLORS: Record<string, string> = {
  IN_STOCK: 'badge-received',
  SOLD: 'badge-ordered',
  RETURNED: 'badge-warning',
  DEFECTIVE: 'badge-danger',
  QUARANTINE: 'badge-warning',
};

export function SerialNumbers() {
  const toast = useToast();
  const qc = useQueryClient();

  const [filterSkuId, setFilterSkuId] = useState('');
  const [filterWarehouseId, setFilterWarehouseId] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [showRegister, setShowRegister] = useState(false);
  const [editSerial, setEditSerial] = useState<SerialNumber | null>(null);

  const [regSkuId, setRegSkuId] = useState('');
  const [regWarehouseId, setRegWarehouseId] = useState('');
  const [regSerialNumber, setRegSerialNumber] = useState('');

  const { data: skusResp } = useQuery({ queryKey: ['skus'], queryFn: () => skusApi.list() });
  const { data: whResp } = useQuery({ queryKey: ['warehouses'], queryFn: () => warehousesApi.list() });

  const skus: SKU[] = (skusResp?.data?.data ?? []) as SKU[];
  const warehouses: Warehouse[] = (whResp?.data?.data ?? []) as Warehouse[];

  const { data: serials = [], isLoading, isError } = useQuery({
    queryKey: ['serial-numbers', filterSkuId, filterWarehouseId, filterStatus],
    queryFn: async () => {
      const params = new URLSearchParams({ sku_id: filterSkuId });
      if (filterWarehouseId) params.append('warehouse_id', filterWarehouseId);
      if (filterStatus) params.append('serial_status', filterStatus);
      const r = await apiClient.get(`/modules/serial-numbers/?${params}`);
      return r.data as SerialNumber[];
    },
    enabled: !!filterSkuId,
  });

  const registerMutation = useMutation({
    mutationFn: (payload: unknown) => apiClient.post('/modules/serial-numbers/register', payload),
    onSuccess: () => {
      toast.success('Serial number registered');
      qc.invalidateQueries({ queryKey: ['serial-numbers'] });
      setShowRegister(false);
      setRegSkuId(''); setRegWarehouseId(''); setRegSerialNumber('');
    },
    onError: (e: { response?: { data?: { detail?: string } } }) =>
      toast.error(e.response?.data?.detail ?? 'Registration failed'),
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      apiClient.put(`/modules/serial-numbers/${id}/status`, { status }),
    onSuccess: () => { toast.success('Status updated'); qc.invalidateQueries({ queryKey: ['serial-numbers'] }); setEditSerial(null); },
    onError: () => toast.error('Failed to update status'),
  });

  const skuLabel = (id: string) => skus.find(s => s.id === id)?.sku_code ?? id.slice(0, 8);
  const whLabel = (id: string) => warehouses.find(w => w.id === id)?.code ?? id.slice(0, 8);

  return (
    <div className="page">
      <div className="page-header">
        <h1>Serial Numbers</h1>
        <p>Track individual units by serial number. Requires the <strong>serial-numbers</strong> module installed.</p>
        <div className="page-actions">
          <button onClick={() => setShowRegister(true)}>+ Register Serial</button>
        </div>
      </div>

      <div className="filters">
        <select value={filterSkuId} onChange={e => setFilterSkuId(e.target.value)}>
          <option value="">Select SKU to browse…</option>
          {skus.map(s => <option key={s.id} value={s.id}>{s.sku_code} — {s.name}</option>)}
        </select>
        <select value={filterWarehouseId} onChange={e => setFilterWarehouseId(e.target.value)}>
          <option value="">All warehouses</option>
          {warehouses.map(w => <option key={w.id} value={w.id}>{w.code} — {w.name}</option>)}
        </select>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map(s => <option key={s}>{s}</option>)}
        </select>
      </div>

      {showRegister && (
        <div className="modal-backdrop" onClick={() => setShowRegister(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Register Serial Number</h2>
              <button className="modal-close" onClick={() => setShowRegister(false)}>✕</button>
            </div>
            <form onSubmit={e => { e.preventDefault(); registerMutation.mutate({ sku_id: regSkuId, warehouse_id: regWarehouseId, serial_number: regSerialNumber }); }}>
              <label>SKU (must have <code>is_serialized: true</code>)
                <select value={regSkuId} onChange={e => setRegSkuId(e.target.value)} required>
                  <option value="">Select SKU…</option>
                  {skus.map(s => <option key={s.id} value={s.id}>{s.sku_code} — {s.name}</option>)}
                </select>
              </label>
              <label style={{ marginTop: '0.75rem', display: 'block' }}>Warehouse
                <select value={regWarehouseId} onChange={e => setRegWarehouseId(e.target.value)} required>
                  <option value="">Select warehouse…</option>
                  {warehouses.map(w => <option key={w.id} value={w.id}>{w.code} — {w.name}</option>)}
                </select>
              </label>
              <label style={{ marginTop: '0.75rem', display: 'block' }}>Serial Number
                <input value={regSerialNumber} onChange={e => setRegSerialNumber(e.target.value)} required placeholder="SN-00123" />
              </label>
              <div className="modal-footer">
                <button type="button" className="outline" onClick={() => setShowRegister(false)}>Cancel</button>
                <button type="submit" disabled={registerMutation.isPending}>{registerMutation.isPending ? 'Registering…' : 'Register'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {editSerial && (
        <div className="modal-backdrop" onClick={() => setEditSerial(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 400 }}>
            <div className="modal-header">
              <h2>Update Status — {editSerial.serial_number}</h2>
              <button className="modal-close" onClick={() => setEditSerial(null)}>✕</button>
            </div>
            <label>New Status
              <select defaultValue={editSerial.status}
                onChange={e => updateStatusMutation.mutate({ id: editSerial.id, status: e.target.value })}>
                {STATUSES.map(s => <option key={s}>{s}</option>)}
              </select>
            </label>
            <div className="modal-footer">
              <button type="button" className="outline" onClick={() => setEditSerial(null)}>Close</button>
            </div>
          </div>
        </div>
      )}

      {!filterSkuId ? (
        <div className="empty-state card"><h3>Select a SKU above to view its serial numbers</h3></div>
      ) : isLoading ? (
        <div className="loading">Loading serials</div>
      ) : isError ? (
        <div className="empty-state card" style={{ color: 'var(--color-red)' }}>
          <h3>Module not active</h3>
          <p>The <strong>serial-numbers</strong> module must be installed and active for this tenant.</p>
        </div>
      ) : (serials as SerialNumber[]).length === 0 ? (
        <div className="empty-state card"><h3>No serial numbers found</h3></div>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Serial Number</th><th>SKU</th><th>Warehouse</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {(serials as SerialNumber[]).map(s => (
                <tr key={s.id}>
                  <td className="mono"><strong>{s.serial_number}</strong></td>
                  <td>{skuLabel(s.sku_id)}</td>
                  <td>{whLabel(s.warehouse_id)}</td>
                  <td><span className={`badge ${STATUS_COLORS[s.status] ?? ''}`}>{s.status}</span></td>
                  <td><button className="btn-sm secondary" onClick={() => setEditSerial(s)}>Update Status</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
