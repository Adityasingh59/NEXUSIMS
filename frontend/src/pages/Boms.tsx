import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { bomsApi, type BOM } from '../api/boms';
import { skusApi, type SKU } from '../api/skus';

type LineForm = { component_sku_id: string; quantity: number; unit_cost_snapshot: number };

export function Boms() {
    const [showCreate, setShowCreate] = useState(false);
    const [editingBom, setEditingBom] = useState<BOM | null>(null);
    const [explodeBom, setExplodeBom] = useState<BOM | null>(null);
    const [explodeQty, setExplodeQty] = useState(1);
    const [explodeResult, setExplodeResult] = useState<Record<string, number> | null>(null);
    const [includeInactive, setIncludeInactive] = useState(false);

    // Form state
    const [formSkuId, setFormSkuId] = useState('');
    const [formName, setFormName] = useState('');
    const [formLines, setFormLines] = useState<LineForm[]>([{ component_sku_id: '', quantity: 1, unit_cost_snapshot: 0 }]);

    const { data: bomsData, refetch } = useQuery({
        queryKey: ['boms', includeInactive],
        queryFn: async () => { const r = await bomsApi.list({ include_inactive: includeInactive }); return r.data?.data ?? []; },
    });
    const { data: skusData } = useQuery({
        queryKey: ['skus'],
        queryFn: async () => { const r = await skusApi.list(); return r.data?.data ?? []; },
    });

    const boms = (bomsData ?? []) as BOM[];
    const skus = (skusData ?? []) as SKU[];

    const resetForm = () => {
        setFormSkuId(''); setFormName('');
        setFormLines([{ component_sku_id: '', quantity: 1, unit_cost_snapshot: 0 }]);
        setShowCreate(false); setEditingBom(null);
    };

    const openEdit = (bom: BOM) => {
        setEditingBom(bom);
        setFormSkuId(bom.sku_id);
        setFormName(bom.name);
        setFormLines(bom.lines.map(l => ({ component_sku_id: l.component_sku_id, quantity: Number(l.quantity), unit_cost_snapshot: Number(l.unit_cost_snapshot) })));
        setShowCreate(false);
    };

    const openCreate = () => { resetForm(); setShowCreate(true); };

    const addLine = () => setFormLines([...formLines, { component_sku_id: '', quantity: 1, unit_cost_snapshot: 0 }]);
    const removeLine = (i: number) => setFormLines(formLines.filter((_, idx) => idx !== i));
    const updateLine = (i: number, key: keyof LineForm, value: string | number) => {
        const next = [...formLines];
        (next[i] as Record<string, unknown>)[key] = key === 'component_sku_id' ? value : Number(value);
        setFormLines(next);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        const validLines = formLines.filter(l => l.component_sku_id && l.quantity > 0);
        if (validLines.length === 0) return;
        try {
            if (editingBom) {
                await bomsApi.update(editingBom.id, { name: formName, lines: validLines });
            } else {
                await bomsApi.create({ sku_id: formSkuId, name: formName, lines: validLines });
            }
            resetForm();
            refetch();
        } catch (err) { console.error(err); }
    };

    const handleArchive = async (id: string) => {
        try { await bomsApi.archive(id); refetch(); } catch (err) { console.error(err); }
    };

    const handleExplode = async () => {
        if (!explodeBom) return;
        try {
            const r = await bomsApi.explode(explodeBom.id, explodeQty);
            setExplodeResult(r.data?.data?.components ?? {});
        } catch (err) { console.error(err); }
    };

    const skuCode = (id: string) => skus.find(s => s.id === id)?.sku_code ?? id.slice(0, 8) + '…';

    return (
        <div className="page boms">
            <h1>Bill of Materials</h1>
            <p>Define component recipes for finished SKUs. Used for COGS calculation and production planning.</p>

            <div className="filters" style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem' }}>
                <button onClick={openCreate}>+ New BOM</button>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input type="checkbox" checked={includeInactive} onChange={e => { setIncludeInactive(e.target.checked); }} />
                    Show archived
                </label>
            </div>

            {(showCreate || editingBom) && (
                <form onSubmit={handleSubmit} className="form">
                    <h2>{editingBom ? 'Edit BOM' : 'Create BOM'}</h2>
                    {!editingBom && (
                        <label>Finished SKU
                            <select value={formSkuId} onChange={e => setFormSkuId(e.target.value)} required>
                                <option value="">Select SKU…</option>
                                {skus.map(s => <option key={s.id} value={s.id}>{s.sku_code} — {s.name}</option>)}
                            </select>
                        </label>
                    )}
                    <label>BOM Name
                        <input value={formName} onChange={e => setFormName(e.target.value)} required maxLength={255} placeholder="e.g. Standard Recipe v1" />
                    </label>
                    <h3>Component Lines</h3>
                    {formLines.map((line, i) => (
                        <div key={i} className="schema-row">
                            <select value={line.component_sku_id} onChange={e => updateLine(i, 'component_sku_id', e.target.value)} required>
                                <option value="">Component SKU…</option>
                                {skus.map(s => <option key={s.id} value={s.id}>{s.sku_code}</option>)}
                            </select>
                            <input type="number" value={line.quantity || ''} onChange={e => updateLine(i, 'quantity', e.target.value)} placeholder="Qty/unit" required min="0.0001" step="0.0001" style={{ width: '90px' }} />
                            <input type="number" value={line.unit_cost_snapshot || ''} onChange={e => updateLine(i, 'unit_cost_snapshot', e.target.value)} placeholder="Unit cost ($)" required min="0" step="0.01" style={{ width: '120px' }} />
                            <button type="button" onClick={() => removeLine(i)} disabled={formLines.length === 1}>Remove</button>
                        </div>
                    ))}
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                        <button type="button" onClick={addLine}>+ Add Component</button>
                        <button type="submit">{editingBom ? 'Save Changes' : 'Create BOM'}</button>
                        <button type="button" onClick={resetForm}>Cancel</button>
                    </div>
                </form>
            )}

            {explodeBom && (
                <div className="form" style={{ marginTop: '1rem' }}>
                    <h2>Explode BOM: {explodeBom.name}</h2>
                    <label>Production Quantity
                        <input type="number" value={explodeQty} onChange={e => setExplodeQty(Number(e.target.value))} min="0.01" step="0.01" style={{ width: '100px', marginLeft: '0.5rem' }} />
                    </label>
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                        <button onClick={handleExplode}>Calculate</button>
                        <button onClick={() => { setExplodeBom(null); setExplodeResult(null); }}>Close</button>
                    </div>
                    {explodeResult && (
                        <table className="table" style={{ marginTop: '0.5rem' }}>
                            <thead><tr><th>Component SKU</th><th>Total Quantity Needed</th></tr></thead>
                            <tbody>
                                {Object.entries(explodeResult).map(([skuId, qty]) => (
                                    <tr key={skuId}><td>{skuCode(skuId)}</td><td>{Number(qty).toFixed(4)}</td></tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            )}

            <table className="table" style={{ marginTop: '1rem' }}>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Finished SKU</th>
                        <th>Components</th>
                        <th>Status</th>
                        <th>Created</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {boms.map(bom => (
                        <tr key={bom.id} style={{ opacity: bom.is_active ? 1 : 0.5 }}>
                            <td>{bom.name}</td>
                            <td>{skuCode(bom.sku_id)}</td>
                            <td>{bom.lines.length} component{bom.lines.length !== 1 ? 's' : ''}</td>
                            <td>{bom.is_active ? '✅ Active' : '🗃️ Archived'}</td>
                            <td>{bom.created_at ? new Date(bom.created_at).toLocaleDateString() : '—'}</td>
                            <td>
                                <button type="button" onClick={() => openEdit(bom)} disabled={!bom.is_active} style={{ marginRight: '0.25rem' }}>Edit</button>
                                <button type="button" onClick={() => { setExplodeBom(bom); setExplodeResult(null); }} style={{ marginRight: '0.25rem' }}>Explode</button>
                                {bom.is_active && <button type="button" onClick={() => handleArchive(bom.id)}>Archive</button>}
                            </td>
                        </tr>
                    ))}
                    {boms.length === 0 && <tr><td colSpan={6} style={{ textAlign: 'center', color: '#888' }}>No BOMs found. Create one above.</td></tr>}
                </tbody>
            </table>
        </div>
    );
}
