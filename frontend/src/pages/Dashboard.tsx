import { useQuery } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import { getDashboard, getRecentActivity, getLowStockSkus } from '../api/reports';

export function Dashboard() {
    const { data: kpis, isLoading: kpisLoading } = useQuery({
        queryKey: ['dashboard'],
        queryFn: () => getDashboard().then((r: any) => r.data),
    });
    const { data: activity } = useQuery({
        queryKey: ['recent-activity'],
        queryFn: () => getRecentActivity().then((r: any) => r.data),
    });
    const { data: lowStock } = useQuery({
        queryKey: ['low-stock'],
        queryFn: () => getLowStockSkus().then((r: any) => r.data),
    });

    const [layout, setLayout] = useState({
        showKpis: true,
        showActivity: true,
        showLowStock: true,
    });
    const [showSettings, setShowSettings] = useState(false);

    useEffect(() => {
        const saved = localStorage.getItem('nexus_dashboard_layout');
        if (saved) {
            try { setLayout(JSON.parse(saved)); } catch (e) { }
        }
    }, []);

    const toggleLayout = (key: keyof typeof layout) => {
        const next = { ...layout, [key]: !layout[key] };
        setLayout(next);
        localStorage.setItem('nexus_dashboard_layout', JSON.stringify(next));
    };

    if (kpisLoading) return <div className="loading">Loading dashboard</div>;

    const kpiCards = [
        { label: 'Total SKUs', value: kpis?.total_skus ?? '—', sub: 'Active products' },
        { label: 'Stock Value', value: kpis?.total_stock_value != null ? `${kpis?.currency_symbol || '$'}${Number(kpis.total_stock_value).toLocaleString()}` : '—', sub: 'At cost' },
        { label: 'Low Stock', value: kpis?.low_stock_count ?? '—', sub: 'Below reorder point' },
        { label: 'Pending Transfers', value: kpis?.pending_transfers ?? '—', sub: 'In transit' },
        { label: 'Transactions (24h)', value: kpis?.recent_transactions_24h ?? '—', sub: 'Last 24 hours' },
        { label: 'Warehouses', value: kpis?.active_warehouses ?? '—', sub: 'Active locations' },
    ];

    const badgeClass = (type: string) => {
        if (type?.includes('RECEIVE') || type?.includes('RETURN')) return 'receive';
        if (type?.includes('PICK')) return 'pick';
        if (type?.includes('ADJUST') || type?.includes('COUNT')) return 'adjust';
        return 'transfer';
    };

    return (
        <div className="page">
            <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1>Dashboard</h1>
                    <p>Real-time inventory overview</p>
                </div>
                <div style={{ position: 'relative' }}>
                    <button onClick={() => setShowSettings(!showSettings)} style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '1.5rem', cursor: 'pointer' }}>⚙️</button>
                    {showSettings && (
                        <div style={{ position: 'absolute', right: 0, top: '100%', background: '#1c2128', border: '1px solid #30363d', borderRadius: '6px', padding: '1rem', zIndex: 10, minWidth: '200px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }}>
                            <h4 style={{ marginBottom: '0.75rem', color: '#8b949e' }}>Widget Settings</h4>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', cursor: 'pointer' }}>
                                <input type="checkbox" checked={layout.showKpis} onChange={() => toggleLayout('showKpis')} /> KPI Overview
                            </label>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', cursor: 'pointer' }}>
                                <input type="checkbox" checked={layout.showActivity} onChange={() => toggleLayout('showActivity')} /> Recent Activity
                            </label>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                <input type="checkbox" checked={layout.showLowStock} onChange={() => toggleLayout('showLowStock')} /> Low Stock Alerts
                            </label>
                        </div>
                    )}
                </div>
            </div>

            {layout.showKpis && (
                <div className="kpi-grid">
                    {kpiCards.map(k => (
                        <div className="kpi-card" key={k.label}>
                            <div className="kpi-label">{k.label}</div>
                            <div className="kpi-value">{k.value}</div>
                            <div className="kpi-sub">{k.sub}</div>
                        </div>
                    ))}
                </div>
            )}

            <div className="dashboard-grid">
                {layout.showActivity && (
                    <div className="card">
                        <h2 style={{ marginBottom: '0.75rem' }}>Recent Activity</h2>
                        {(activity?.length ?? 0) === 0 ? (
                            <div className="empty-state"><h3>No recent activity</h3></div>
                        ) : (
                            activity?.slice(0, 15).map((a: any) => (
                                <div className="activity-item" key={a.id}>
                                    <span className={`activity-badge ${badgeClass(a.event_type)}`}>{a.event_type}</span>
                                    <span className="truncate" style={{ flex: 1 }}>
                                        <strong>{a.sku_code}</strong> · {a.sku_name}
                                    </span>
                                    <span className="mono" style={{ color: Number(a.quantity_delta) >= 0 ? 'var(--color-green)' : 'var(--color-red)' }}>
                                        {Number(a.quantity_delta) >= 0 ? '+' : ''}{a.quantity_delta}
                                    </span>
                                    <span className="text-xs text-muted">{a.warehouse_code}</span>
                                </div>
                            ))
                        )}
                    </div>
                )}

                {layout.showLowStock && (
                    <div className="card">
                        <h2 style={{ marginBottom: '0.75rem' }}>Low Stock Alerts</h2>
                        {(lowStock?.length ?? 0) === 0 ? (
                            <div className="empty-state"><h3>All stock levels healthy</h3></div>
                        ) : (
                            lowStock?.slice(0, 8).map((s: any) => (
                                <div key={s.sku_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.45rem 0', borderBottom: '1px solid var(--color-edge-2)', fontSize: '0.8125rem' }}>
                                    <div>
                                        <strong>{s.sku_code}</strong>
                                        <div className="text-xs text-muted">{s.sku_name}</div>
                                    </div>
                                    <div style={{ textAlign: 'right' }}>
                                        <span className={`badge ${s.current_stock === 0 ? 'badge-danger' : 'badge-warning'}`}>
                                            {s.current_stock} / {s.reorder_point}
                                        </span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
