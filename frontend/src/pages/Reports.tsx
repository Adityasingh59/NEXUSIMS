import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getStockValuation, getLowStockSkus, getMovementHistory } from '../api/reports';
import { useAppStore } from '../stores/useAppStore';

type Tab = 'valuation' | 'low-stock' | 'movement';

function exportCsv(filename: string, headers: string[], rows: (string | number | null | undefined)[][]) {
    const escape = (v: unknown) => {
        const s = v == null ? '' : String(v);
        return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const csv = [headers, ...rows].map(r => r.map(escape).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
}

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

    const rows = (data?.data || []) as Record<string, unknown>[];
    const totalValue = data?.meta?.total_value ?? 0;

    const handleExport = () => {
        exportCsv(
            `stock-valuation-${new Date().toISOString().slice(0, 10)}.csv`,
            ['SKU Code', 'Name', 'Warehouse', 'Stock Level', 'Unit Cost', 'Total Value'],
            rows.map(r => [r.sku_code, r.sku_name, r.warehouse_code, r.stock_level, r.unit_cost, r.total_value] as (string | number | null)[])
        );
    };

    return (
        <>
            <div style={{ marginBottom: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="text-sm text-muted">{rows.length} items · Total: <strong>${Number(totalValue).toLocaleString()}</strong></span>
                <button className="outline btn-sm" onClick={handleExport} disabled={rows.length === 0}>⬇ Export CSV</button>
            </div>
            <div className="table-wrap">
                <table className="table">
                    <thead><tr>
                        <th>SKU</th><th>Name</th><th>Warehouse</th><th style={{ textAlign: 'right' }}>Stock</th><th style={{ textAlign: 'right' }}>Unit Cost</th><th style={{ textAlign: 'right' }}>Value</th>
                    </tr></thead>
                    <tbody>
                        {rows.length === 0 ? (
                            <tr><td colSpan={6}><div className="empty-state"><h3>No stock data</h3></div></td></tr>
                        ) : rows.map((r) => (
                            <tr key={`${r.sku_id}-${r.warehouse_id}`}>
                                <td className="mono">{r.sku_code as string}</td>
                                <td>{r.sku_name as string}</td>
                                <td className="mono">{r.warehouse_code as string}</td>
                                <td style={{ textAlign: 'right' }}>{r.stock_level as number}</td>
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
    const rows = (data?.data || []) as Record<string, unknown>[];

    const handleExport = () => {
        exportCsv(
            `low-stock-${new Date().toISOString().slice(0, 10)}.csv`,
            ['SKU Code', 'Name', 'Current Stock', 'Reorder Point', 'Deficit', 'Unit Cost'],
            rows.map(r => [r.sku_code, r.sku_name, r.current_stock, r.reorder_point, r.deficit, r.unit_cost] as (string | number | null)[])
        );
    };

    return (
        <>
            <div style={{ marginBottom: '0.75rem', display: 'flex', justifyContent: 'flex-end' }}>
                <button className="outline btn-sm" onClick={handleExport} disabled={rows.length === 0}>⬇ Export CSV</button>
            </div>
            <div className="table-wrap">
                <table className="table">
                    <thead><tr>
                        <th>SKU</th><th>Name</th><th style={{ textAlign: 'right' }}>Current</th><th style={{ textAlign: 'right' }}>Reorder Point</th><th style={{ textAlign: 'right' }}>Deficit</th>
                    </tr></thead>
                    <tbody>
                        {rows.length === 0 ? (
                            <tr><td colSpan={5}><div className="empty-state"><h3>All stock levels healthy</h3></div></td></tr>
                        ) : rows.map((r) => (
                            <tr key={r.sku_id as string}>
                                <td className="mono">{r.sku_code as string}</td>
                                <td>{r.sku_name as string}</td>
                                <td style={{ textAlign: 'right' }}>
                                    <span className={`badge ${r.current_stock === 0 ? 'badge-danger' : 'badge-warning'}`}>{r.current_stock as number}</span>
                                </td>
                                <td style={{ textAlign: 'right' }}>{r.reorder_point as number}</td>
                                <td style={{ textAlign: 'right', color: 'var(--color-red)', fontWeight: 600 }}>-{r.deficit as number}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </>
    );
}

function MovementTab({ warehouseId }: { warehouseId: string | null }) {
    const { data, isLoading } = useQuery({
        queryKey: ['movement-history', warehouseId],
        queryFn: () => getMovementHistory({ warehouse_id: warehouseId || undefined }),
    });

    if (isLoading) return <div className="loading">Loading</div>;
    const rows = (data?.data?.summary || []) as Record<string, unknown>[];

    const handleExport = () => {
        exportCsv(
            `movement-history-${new Date().toISOString().slice(0, 10)}.csv`,
            ['Event Type', 'Count', 'Total Quantity'],
            rows.map(r => [r.event_type, r.count, r.total_quantity] as (string | number)[])
        );
    };

    const badgeClass = (type: string) => {
        if (type?.includes('RECEIVE') || type?.includes('RETURN')) return 'badge-received';
        if (type?.includes('PICK')) return 'badge-partial';
        if (type?.includes('ADJUST') || type?.includes('COUNT')) return 'badge-ordered';
        return 'badge-in_transit';
    };

    return (
        <>
            <div style={{ marginBottom: '0.75rem', display: 'flex', justifyContent: 'flex-end' }}>
                <button className="outline btn-sm" onClick={handleExport} disabled={rows.length === 0}>⬇ Export CSV</button>
            </div>
            <div className="table-wrap">
                <table className="table">
                    <thead><tr>
                        <th>Event Type</th><th style={{ textAlign: 'right' }}>Count</th><th style={{ textAlign: 'right' }}>Total Quantity</th>
                    </tr></thead>
                    <tbody>
                        {rows.length === 0 ? (
                            <tr><td colSpan={3}><div className="empty-state"><h3>No movement data</h3></div></td></tr>
                        ) : rows.map((r) => (
                            <tr key={r.event_type as string}>
                                <td><span className={`badge ${badgeClass(r.event_type as string)}`}>{r.event_type as string}</span></td>
                                <td style={{ textAlign: 'right' }}>{r.count as number}</td>
                                <td style={{ textAlign: 'right', fontWeight: 600 }}>{Number(r.total_quantity).toLocaleString()}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </>
    );
}
