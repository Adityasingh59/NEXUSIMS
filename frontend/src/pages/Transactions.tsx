import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { transactionsApi } from '../api/transactions';
import { warehousesApi } from '../api/warehouses';
import { skusApi } from '../api/skus';
import type { Warehouse } from '../api/warehouses';
import type { SKU } from '../api/skus';

export function Transactions() {
  const [skuId, setSkuId] = useState('');
  const [warehouseId, setWarehouseId] = useState('');
  const [quantity, setQuantity] = useState('');
  const [eventType, setEventType] = useState('RECEIVE');

  const { data: whData } = useQuery({
    queryKey: ['warehouses'],
    queryFn: async () => {
      const r = await warehousesApi.list();
      return r.data?.data ?? [];
    },
  });

  const { data: skusData } = useQuery({
    queryKey: ['skus'],
    queryFn: async () => {
      const r = await skusApi.list();
      return r.data?.data ?? [];
    },
  });

  const { data: txData, refetch } = useQuery({
    queryKey: ['transactions', skuId, warehouseId],
    queryFn: async () => {
      const r = await transactionsApi.list({
        sku_id: skuId || undefined,
        warehouse_id: warehouseId || undefined,
        page_size: 20,
      });
      return r.data;
    },
  });

  const warehouses = (whData ?? []) as Warehouse[];
  const skus = (skusData ?? []) as SKU[];
  const transactions = (txData?.data ?? []) as Array<{
    id: string;
    sku_id: string;
    warehouse_id: string;
    event_type: string;
    quantity_delta: number;
    running_balance: number;
    created_at: string;
  }>;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const qty = parseFloat(quantity);
    if (!skuId || !warehouseId || isNaN(qty)) return;
    try {
      if (eventType === 'RECEIVE') await transactionsApi.receive({ sku_id: skuId, warehouse_id: warehouseId, quantity: qty });
      else if (eventType === 'PICK') await transactionsApi.pick({ sku_id: skuId, warehouse_id: warehouseId, quantity: qty });
      setQuantity('');
      refetch();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="page transactions">
      <h1>Stock Ledger & Transactions</h1>
      <p>Post RECEIVE, PICK, ADJUST, or RETURN events. Append-only ledger.</p>

      <form onSubmit={handleSubmit} className="form">
        <h2>Post Transaction</h2>
        <label>
          SKU <select value={skuId} onChange={e => setSkuId(e.target.value)} required>
            <option value="">Select...</option>
            {skus.map(s => <option key={s.id} value={s.id}>{s.sku_code} – {s.name}</option>)}
          </select>
        </label>
        <label>
          Warehouse <select value={warehouseId} onChange={e => setWarehouseId(e.target.value)} required>
            <option value="">Select...</option>
            {warehouses.map(w => <option key={w.id} value={w.id}>{w.code} – {w.name}</option>)}
          </select>
        </label>
        <label>
          Event <select value={eventType} onChange={e => setEventType(e.target.value)}>
            <option value="RECEIVE">RECEIVE (inbound)</option>
            <option value="PICK">PICK (outbound)</option>
          </select>
        </label>
        <label>
          Quantity <input type="number" value={quantity} onChange={e => setQuantity(e.target.value)} required step="0.01" />
        </label>
        <button type="submit">Post</button>
      </form>

      <h2>Transaction History</h2>
      <div className="filters">
        <select value={skuId} onChange={e => setSkuId(e.target.value)}>
          <option value="">All SKUs</option>
          {skus.map(s => <option key={s.id} value={s.id}>{s.sku_code}</option>)}
        </select>
        <select value={warehouseId} onChange={e => setWarehouseId(e.target.value)}>
          <option value="">All warehouses</option>
          {warehouses.map(w => <option key={w.id} value={w.id}>{w.code}</option>)}
        </select>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Time</th>
            <th>SKU</th>
            <th>Warehouse</th>
            <th>Event</th>
            <th>Delta</th>
            <th>Balance</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map(tx => (
            <tr key={tx.id}>
              <td>{tx.created_at ? new Date(tx.created_at).toLocaleString() : '-'}</td>
              <td>{skus.find(s => s.id === tx.sku_id)?.sku_code ?? tx.sku_id}</td>
              <td>{warehouses.find(w => w.id === tx.warehouse_id)?.code ?? tx.warehouse_id}</td>
              <td>{tx.event_type}</td>
              <td>{tx.quantity_delta}</td>
              <td>{tx.running_balance ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
