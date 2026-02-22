import { useQuery } from '@tanstack/react-query';
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

    if (kpisLoading) return <div className="loading">Loading dashboard</div>;

    const kpiCards = [
        { label: 'Total SKUs', value: kpis?.total_skus ?? '—', sub: 'Active products' },
        { label: 'Stock Value', value: kpis?.total_stock_value != null ? `$${Number(kpis.total_stock_value).toLocaleString()}` : '—', sub: 'At cost' },
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
            <div className="page-header">
                <h1>Dashboard</h1>
                <p>Real-time inventory overview</p>
            </div>

            <div className="kpi-grid">
                {kpiCards.map(k => (
                    <div className="kpi-card" key={k.label}>
                        <div className="kpi-label">{k.label}</div>
                        <div className="kpi-value">{k.value}</div>
                        <div className="kpi-sub">{k.sub}</div>
                    </div>
                ))}
            </div>

            <div className="dashboard-grid">
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
            </div>
        </div>
    );
}
