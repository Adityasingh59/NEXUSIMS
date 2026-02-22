import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { getBOMs, createBOM, checkBOMAvailability } from '../api/assembly';
import { skusApi, type SKU } from '../api/skus';

type LineForm = { uuid: string; component_sku_id: string; quantity: number; unit: string };

export function Boms() {
    const queryClient = useQueryClient();
    const [showCreate, setShowCreate] = useState(false);
    const [includeInactive, setIncludeInactive] = useState(false);

    // Form state
    const [formFinishedSkuId, setFormFinishedSkuId] = useState('');
    const [formLandedCost, setFormLandedCost] = useState<number>(0);
    const [formLandedCostDesc, setFormLandedCostDesc] = useState('');
    const [formLines, setFormLines] = useState<LineForm[]>([{ uuid: Math.random().toString(), component_sku_id: '', quantity: 1, unit: '' }]);

    // Availability Check State
    const [checkBomId, setCheckBomId] = useState<string | null>(null);
    const [checkQty, setCheckQty] = useState<number>(1);
    const [availabilityResult, setAvailabilityResult] = useState<any | null>(null);

    const { data: bomsData, isLoading: bomsLoading } = useQuery({
        queryKey: ['boms', includeInactive],
        queryFn: async () => await getBOMs({ include_inactive: includeInactive }),
    });

    const { data: skusData } = useQuery({
        queryKey: ['skus'],
        queryFn: async () => { const r = await skusApi.list(); return r.data?.data ?? []; },
    });

    const boms = bomsData?.data ?? [];
    const skus = (skusData ?? []) as SKU[];

    const createMutation = useMutation({
        mutationFn: createBOM,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['boms'] });
            resetForm();
        },
        onError: (err) => {
            console.error("Failed to create BOM", err);
            alert("Error creating BOM");
        }
    });

    const resetForm = () => {
        setFormFinishedSkuId('');
        setFormLandedCost(0);
        setFormLandedCostDesc('');
        setFormLines([{ uuid: Math.random().toString(), component_sku_id: '', quantity: 1, unit: '' }]);
        setShowCreate(false);
    };

    const addLine = () => setFormLines([...formLines, { uuid: Math.random().toString(), component_sku_id: '', quantity: 1, unit: '' }]);
    const removeLine = (i: number) => setFormLines(formLines.filter((_, idx) => idx !== i));
    const updateLine = (i: number, key: keyof LineForm, value: string | number) => {
        const next = [...formLines];
        (next[i] as any)[key] = value;
        setFormLines(next);
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const validLines = formLines.filter(l => l.component_sku_id && l.quantity > 0);
        if (validLines.length === 0 || !formFinishedSkuId) {
            alert("Please select a finished SKU and add at least one valid component line.");
            return;
        }

        const payload = {
            finished_sku_id: formFinishedSkuId,
            landed_cost: formLandedCost,
            landed_cost_description: formLandedCostDesc || null,
            lines: validLines.map(l => ({
                component_sku_id: l.component_sku_id,
                quantity: l.quantity,
                unit: l.unit || null
            }))
        };

        createMutation.mutate(payload);
    };

    const handleCheckAvailability = async () => {
        if (!checkBomId || checkQty <= 0) return;
        try {
            const result = await checkBOMAvailability(checkBomId, checkQty);
            setAvailabilityResult(result);
        } catch (err) {
            console.error(err);
            alert("Failed to check availability");
        }
    };

    const skuCode = (id: string) => skus.find(s => s.id === id)?.sku_code ?? id.slice(0, 8) + '…';
    const skuName = (id: string) => skus.find(s => s.id === id)?.name ?? 'Unknown SKU';

    return (
        <div className="page boms">
            <h1>Bills of Materials</h1>
            <p>Define assembly recipes for finished goods. Creating a new BOM for an existing SKU will version it.</p>

            <div className="filters" style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem' }}>
                <button onClick={() => setShowCreate(true)} className="btn primary">+ New BOM</button>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input type="checkbox" checked={includeInactive} onChange={e => setIncludeInactive(e.target.checked)} />
                    Show historical versions
                </label>
            </div>

            {showCreate && (
                <form onSubmit={handleSubmit} className="form" style={{ marginBottom: '2rem', padding: '1.5rem', background: 'var(--color-surface)', borderRadius: '8px', border: '1px solid var(--color-edge)' }}>
                    <h2 style={{ marginTop: 0 }}>Create BOM Version</h2>
                    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
                        <div>
                            <label>Finished SKU</label>
                            <select value={formFinishedSkuId} onChange={e => setFormFinishedSkuId(e.target.value)} required>
                                <option value="">Select SKU...</option>
                                {skus.map(s => <option key={s.id} value={s.id}>{s.sku_code} - {s.name}</option>)}
                            </select>
                        </div>
                        <div>
                            <label>Fixed Landed Cost (Overhead)</label>
                            <input type="number" step="0.01" min="0" value={formLandedCost} onChange={e => setFormLandedCost(Number(e.target.value))} />
                        </div>
                        <div style={{ gridColumn: 'span 2' }}>
                            <label>Landed Cost Description</label>
                            <input type="text" placeholder="e.g. Labor and machinery overhead per run" value={formLandedCostDesc} onChange={e => setFormLandedCostDesc(e.target.value)} />
                        </div>
                    </div>

                    <h3>Components</h3>
                    {formLines.map((line, i) => (
                        <div key={line.uuid} style={{ display: 'flex', gap: '1rem', marginBottom: '0.75rem', alignItems: 'flex-end', borderBottom: '1px solid var(--color-edge)', paddingBottom: '0.5rem' }}>
                            <div style={{ flex: 2 }}>
                                <label>Component SKU</label>
                                <select value={line.component_sku_id} onChange={e => updateLine(i, 'component_sku_id', e.target.value)} required>
                                    <option value="">Select Component...</option>
                                    {skus.filter(s => s.id !== formFinishedSkuId).map(s => <option key={s.id} value={s.id}>{s.sku_code} - {s.name}</option>)}
                                </select>
                            </div>
                            <div style={{ flex: 1 }}>
                                <label>Qty / Finished Unit</label>
                                <input type="number" step="0.0001" min="0.0001" value={line.quantity} onChange={e => updateLine(i, 'quantity', Number(e.target.value))} required />
                            </div>
                            <div style={{ flex: 1 }}>
                                <label>Unit</label>
                                <input type="text" placeholder="e.g. kg, pcs" value={line.unit || ''} onChange={e => updateLine(i, 'unit', e.target.value)} />
                            </div>
                            {formLines.length > 1 && (
                                <button type="button" onClick={() => removeLine(i)} className="btn danger" style={{ padding: '0.5rem 1rem', marginBottom: '4px' }}>X</button>
                            )}
                        </div>
                    ))}
                    <button type="button" onClick={addLine} className="btn outline" style={{ marginTop: '0.5rem' }}>+ Add Component</button>

                    <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem' }}>
                        <button type="submit" className="btn primary" disabled={createMutation.isPending}>
                            {createMutation.isPending ? 'Saving...' : 'Save BOM'}
                        </button>
                        <button type="button" onClick={resetForm} className="btn text">Cancel</button>
                    </div>
                </form>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(0, 1fr)', gap: '2rem' }}>
                <div className="table-container">
                    {bomsLoading ? (
                        <p>Loading BOMs...</p>
                    ) : (
                        <table>
                            <thead>
                                <tr>
                                    <th>Finished SKU</th>
                                    <th>Version</th>
                                    <th>Status</th>
                                    <th>Components</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {boms.map(bom => (
                                    <tr key={bom.id} style={{ opacity: bom.is_active ? 1 : 0.6 }}>
                                        <td><strong>{skuCode(bom.finished_sku_id)}</strong><br /><small>{skuName(bom.finished_sku_id)}</small></td>
                                        <td>v{bom.version}</td>
                                        <td>
                                            <span style={{
                                                padding: '2px 8px', borderRadius: '12px', fontSize: '0.8rem',
                                                background: bom.is_active ? 'rgba(76, 175, 80, 0.1)' : 'rgba(158, 158, 158, 0.1)',
                                                color: bom.is_active ? '#4CAF50' : '#9E9E9E'
                                            }}>
                                                {bom.is_active ? 'Active' : 'Historical'}
                                            </span>
                                        </td>
                                        <td>{bom.lines.length} lines</td>
                                        <td>
                                            {bom.is_active && (
                                                <button onClick={() => { setCheckBomId(bom.id); setAvailabilityResult(null); }} className="btn outline sm">
                                                    Check Stock
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                                {boms.length === 0 && (
                                    <tr><td colSpan={5} style={{ textAlign: 'center', padding: '2rem' }}>No BOMs defined yet.</td></tr>
                                )}
                            </tbody>
                        </table>
                    )}
                </div>

                <div className="availability-panel" style={{ padding: '1.5rem', background: 'var(--color-surface)', borderRadius: '8px', border: '1px solid var(--color-edge)', height: 'fit-content' }}>
                    <h3 style={{ marginTop: 0 }}>Availability Checker</h3>
                    <p style={{ fontSize: '0.9rem', color: 'var(--color-white)', opacity: 0.8 }}>Select an active BOM to simulate production capacity and identify component shortages.</p>

                    {checkBomId && (
                        <div style={{ marginTop: '1.5rem' }}>
                            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-end', marginBottom: '1rem' }}>
                                <div style={{ flex: 1 }}>
                                    <label style={{ fontSize: '0.85rem' }}>Target Yield Qty:</label>
                                    <input type="number" min="1" value={checkQty} onChange={e => setCheckQty(Number(e.target.value))} style={{ width: '100%' }} />
                                </div>
                                <button onClick={handleCheckAvailability} className="btn primary">Check</button>
                            </div>

                            {availabilityResult && (
                                <div style={{
                                    marginTop: '1.5rem', padding: '1rem', borderRadius: '8px',
                                    border: `1px solid ${availabilityResult.is_available ? '#4CAF50' : '#f44336'}`,
                                    background: availabilityResult.is_available ? 'rgba(76, 175, 80, 0.05)' : 'rgba(244, 67, 54, 0.05)'
                                }}>
                                    <h4 style={{ color: availabilityResult.is_available ? '#4CAF50' : '#f44336', margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        {availabilityResult.is_available ? '✅ Ready to Assemble' : '❌ Stock Shortage'}
                                    </h4>

                                    {!availabilityResult.is_available && Object.keys(availabilityResult.shortages).length > 0 && (
                                        <div style={{ display: 'grid', gap: '0.5rem' }}>
                                            {Object.entries(availabilityResult.shortages).map(([skuId, data]: [string, any]) => (
                                                <div key={skuId} style={{ padding: '0.75rem', background: 'var(--color-surface)', borderRadius: '4px', borderLeft: '3px solid #f44336', fontSize: '0.9rem' }}>
                                                    <strong>{skuCode(skuId)}</strong> ({skuName(skuId)})
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem', opacity: 0.8 }}>
                                                        <span>Required: {data.required}</span>
                                                        <span>Have: {data.available}</span>
                                                        <span style={{ color: '#f44336', fontWeight: 600 }}>Short: {data.shortage}</span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
