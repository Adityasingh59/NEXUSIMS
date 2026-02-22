import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getStockValuation, getLowStockSkus, getMovementHistory } from '../api/reports';
import { useAppStore } from '../stores/useAppStore';

type Tab = 'valuation' | 'low-stock' | 'movement';

export function Reports() {
    const [tab, setTab] = useState<Tab>('valuation');
    const { warehouseId } = useAppStore();

    return (
        <div className="page">
            <div className="page-header">
                <h1>Reports</h1>
                <p>Inventory analytics and insights</p>
            </div>

            <div style={{ display: 'flex', gap: '0.25rem', marginBottom: '1.25rem', borderBottom: '1px solid var(--color-edge)', paddingBottom: '0.5rem' }}>
                {(['valuation', 'low-stock', 'movement'] as Tab[]).map(t => (
                    <button key={t} onClick={() => setTab(t)}
                        className={tab === t ? '' : 'btn-ghost'}
                        style={tab === t ? {} : { background: 'transparent', color: 'var(--color-mist)' }}>
                        {t === 'valuation' ? 'Stock Valuation' : t === 'low-stock' ? 'Low Stock' : 'Movement History'}
                    </button>
                ))}
            </div>

            {tab === 'valuation' && <StockValuationTab warehouseId={warehouseId} />}
            {tab === 'low-stock' && <LowStockTab />}
            {tab === 'movement' && <MovementTab warehouseId={warehouseId} />}
        </div>
    );
}

function StockValuationTab({ warehouseId }: { warehouseId: string | null }) {
    const { data, isLoading } = useQuery({
        queryKey: ['stock-valuation', warehouseId],
        queryFn: () => getStockValuation(warehouseId || undefined),
    });

    if (isLoading) return <div className="loading">Loading valuation</div>;

    const rows = data?.data || [];
    const totalValue = data?.meta?.total_value ?? 0;

    return (
        <>
            <div style={{ marginBottom: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="text-sm text-muted">{rows.length} items</span>
                <span style={{ fontWeight: 700 }}>Total: ${Number(totalValue).toLocaleString()}</span>
            </div>
            <div className="table-wrap">
                <table className="table">
                    <thead><tr>
                        <th>SKU</th><th>Name</th><th>Warehouse</th><th style={{ textAlign: 'right' }}>Stock</th><th style={{ textAlign: 'right' }}>Unit Cost</th><th style={{ textAlign: 'right' }}>Value</th>
                    </tr></thead>
                    <tbody>
                        {rows.length === 0 ? (
                            <tr><td colSpan={6}><div className="empty-state"><h3>No stock data</h3></div></td></tr>
                        ) : rows.map((r: any) => (
                            <tr key={`${r.sku_id}-${r.warehouse_id}`}>
                                <td className="mono">{r.sku_code}</td>
                                <td>{r.sku_name}</td>
                                <td className="mono">{r.warehouse_code}</td>
                                <td style={{ textAlign: 'right' }}>{r.stock_level}</td>
                                <td style={{ textAlign: 'right' }}>{r.unit_cost != null ? `$${r.unit_cost}` : '—'}</td>
                                <td style={{ textAlign: 'right', fontWeight: 600 }}>{r.total_value != null ? `$${Number(r.total_value).toLocaleString()}` : '—'}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </>
    );
}

function LowStockTab() {
    const { data, isLoading } = useQuery({
        queryKey: ['low-stock-report'],
        queryFn: () => getLowStockSkus(),
    });

    if (isLoading) return <div className="loading">Loading</div>;
    const rows = data?.data || [];

    return (
        <div className="table-wrap">
            <table className="table">
                <thead><tr>
                    <th>SKU</th><th>Name</th><th style={{ textAlign: 'right' }}>Current</th><th style={{ textAlign: 'right' }}>Reorder Point</th><th style={{ textAlign: 'right' }}>Deficit</th>
                </tr></thead>
                <tbody>
                    {rows.length === 0 ? (
                        <tr><td colSpan={5}><div className="empty-state"><h3>All stock levels healthy</h3></div></td></tr>
                    ) : rows.map((r: any) => (
                        <tr key={r.sku_id}>
                            <td className="mono">{r.sku_code}</td>
                            <td>{r.sku_name}</td>
                            <td style={{ textAlign: 'right' }}>
                                <span className={`badge ${r.current_stock === 0 ? 'badge-danger' : 'badge-warning'}`}>{r.current_stock}</span>
                            </td>
                            <td style={{ textAlign: 'right' }}>{r.reorder_point}</td>
                            <td style={{ textAlign: 'right', color: 'var(--color-red)', fontWeight: 600 }}>-{r.deficit}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function MovementTab({ warehouseId }: { warehouseId: string | null }) {
    const { data, isLoading } = useQuery({
        queryKey: ['movement-history', warehouseId],
        queryFn: () => getMovementHistory({ warehouse_id: warehouseId || undefined }),
    });

    if (isLoading) return <div className="loading">Loading</div>;
    const rows = data?.data?.summary || [];

    const badgeClass = (type: string) => {
        if (type?.includes('RECEIVE') || type?.includes('RETURN')) return 'badge-received';
        if (type?.includes('PICK')) return 'badge-partial';
        if (type?.includes('ADJUST') || type?.includes('COUNT')) return 'badge-ordered';
        return 'badge-in_transit';
    };

    return (
        <div className="table-wrap">
            <table className="table">
                <thead><tr>
                    <th>Event Type</th><th style={{ textAlign: 'right' }}>Count</th><th style={{ textAlign: 'right' }}>Total Quantity</th>
                </tr></thead>
                <tbody>
                    {rows.length === 0 ? (
                        <tr><td colSpan={3}><div className="empty-state"><h3>No movement data</h3></div></td></tr>
                    ) : rows.map((r: any) => (
                        <tr key={r.event_type}>
                            <td><span className={`badge ${badgeClass(r.event_type)}`}>{r.event_type}</span></td>
                            <td style={{ textAlign: 'right' }}>{r.count}</td>
                            <td style={{ textAlign: 'right', fontWeight: 600 }}>{Number(r.total_quantity).toLocaleString()}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
