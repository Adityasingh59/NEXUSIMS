import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { warehousesApi } from '../api/warehouses';
import { useAppStore } from '../stores/useAppStore';
import { useAuthStore } from '../stores/useAuthStore';

const NAV = [
  {
    section: 'Overview', items: [
      { to: '/', icon: '◻', label: 'Dashboard' },
      { to: '/reports', icon: '◈', label: 'Reports' },
    ]
  },
  {
    section: 'Inventory', items: [
      { to: '/item-types', icon: '◆', label: 'Item Types' },
      { to: '/skus', icon: '▣', label: 'SKUs' },
      { to: '/transactions', icon: '↕', label: 'Transactions' },
    ]
  },
  {
    section: 'Operations', items: [
      { to: '/warehouses', icon: '⊞', label: 'Warehouses' },
      { to: '/locations', icon: '⊡', label: 'Locations' },
      { to: '/transfers', icon: '⇄', label: 'Transfers' },
      { to: '/boms', icon: '⊟', label: 'BOMs' },
      { to: '/assembly-orders', icon: '⚙', label: 'Assembly' },
      { to: '/sales-orders', icon: '↗', label: 'Outbound Orders' },
      { to: '/purchase-orders', icon: '◧', label: 'Purchase Orders' },
    ]
  },
  {
    section: 'Automation', items: [
      { to: '/workflows', icon: '⟳', label: 'Workflows' },
      { to: '/webhooks', icon: '⊹', label: 'Webhooks' },
    ]
  },
  {
    section: 'Modules', items: [
      { to: '/serial-numbers', icon: '⊕', label: 'Serial Numbers' },
      { to: '/expiry-tracker', icon: '⏱', label: 'Expiry Tracker' },
    ]
  },
  {
    section: 'Settings', items: [
      { to: '/users', icon: '◉', label: 'Users' },
      { to: '/api-keys', icon: '⊙', label: 'API Keys' },
    ]
  },
];

export function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { warehouseId, setWarehouse } = useAppStore();
  const logout = useAuthStore((s) => s.logout);
  const { data: warehouses } = useQuery({
    queryKey: ['warehouses'],
    queryFn: () => warehousesApi.list().then((r) => {
      const responseBody = (r.data || r) as { data?: unknown[] };
      return Array.isArray(responseBody.data) ? responseBody.data : [];
    }),
  });

  // Scanner uses its own layout
  if (location.pathname === '/scanner') {
    return <Outlet />;
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo">NEXUS<span>IMS</span></div>
          <div className="subtitle">Inventory Management</div>
        </div>

        <nav className="sidebar-nav">
          {NAV.map(section => (
            <div className="nav-section" key={section.section}>
              <div className="nav-section-label">{section.section}</div>
              {section.items.map(item => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                >
                  <span className="icon">{item.icon}</span>
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}

          <div className="nav-section" style={{ marginTop: '0.5rem' }}>
            <div className="nav-section-label">Scanner</div>
            <NavLink to="/scanner" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <span className="icon">⎷</span>
              <span>Open Scanner</span>
            </NavLink>
          </div>
        </nav>

        <div className="sidebar-footer">
          <select
            className="warehouse-switcher"
            value={warehouseId || ''}
            onChange={e => setWarehouse(e.target.value || null)}
          >
            <option value="">All Warehouses</option>
            {(warehouses || []).map((w: unknown) => {
              const wh = w as { id: string; code: string; name: string };
              return <option key={wh.id} value={wh.id}>{wh.code} — {wh.name}</option>;
            })}
          </select>
          <button className="btn-logout" onClick={() => { logout(); navigate('/login'); }}>
            ⏻ Logout
          </button>
        </div>
      </aside>

      <main className="main-content">
        <div className="main-inner">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
