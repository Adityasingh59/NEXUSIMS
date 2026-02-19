import { Link, Outlet } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAppStore } from '../stores/useAppStore';
import { warehousesApi } from '../api/warehouses';

export function Layout() {
  const { warehouseId, setWarehouse } = useAppStore();
  const { data } = useQuery({
    queryKey: ['warehouses'],
    queryFn: async () => { const r = await warehousesApi.list(); return r.data?.data ?? []; },
  });
  const warehouses = (data ?? []) as Array<{ id: string; code: string; name: string }>;

  return (
    <div className="layout">
      <header className="layout-header">
        <Link to="/" className="logo">NEXUS IMS</Link>
        <nav>
          <Link to="/">Dashboard</Link>
          <Link to="/item-types">Item Types</Link>
          <Link to="/skus">SKUs</Link>
          <Link to="/warehouses">Warehouses</Link>
          <Link to="/locations">Locations</Link>
          <Link to="/transfers">Transfers</Link>
          <Link to="/transactions">Transactions</Link>
          <select
            value={warehouseId ?? ''}
            onChange={e => setWarehouse(e.target.value || null)}
            className="warehouse-switcher"
            title="Active warehouse"
          >
            <option value="">All warehouses</option>
            {warehouses.map(w => <option key={w.id} value={w.id}>{w.code}</option>)}
          </select>
        </nav>
      </header>
      <main className="layout-main">
        <Outlet />
      </main>
    </div>
  );
}
