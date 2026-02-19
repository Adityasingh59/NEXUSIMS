import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { itemTypesApi, type ItemType } from '../api/itemTypes';
import { skusApi, type SKU } from '../api/skus';
import type { AttributeFieldSchema } from '../api/itemTypes';

export function Skus() {
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState('');
  const [itemTypeId, setItemTypeId] = useState('');
  const [skuCode, setSkuCode] = useState('');
  const [name, setName] = useState('');
  const [attrs, setAttrs] = useState<Record<string, string>>({});
  const [reorderPoint, setReorderPoint] = useState('');
  const [unitCost, setUnitCost] = useState('');

  const { data: typesData } = useQuery({
    queryKey: ['item-types'],
    queryFn: async () => {
      const r = await itemTypesApi.list();
      return r.data?.data ?? [];
    },
  });

  const { data, refetch } = useQuery({
    queryKey: ['skus', search, itemTypeId],
    queryFn: async () => {
      const r = await skusApi.list({
        search: search || undefined,
        item_type_id: itemTypeId || undefined,
      });
      return r.data;
    },
  });

  const types = (typesData ?? []) as ItemType[];
  const skus = (data?.data ?? []) as SKU[];

  const selectedType = types.find(t => t.id === itemTypeId);
  const schema = (selectedType?.attribute_schema ?? []) as AttributeFieldSchema[];

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const attributes: Record<string, unknown> = {};
    schema.forEach(f => {
      const v = attrs[f.name];
      if (v !== undefined && v !== '') {
        if (f.type === 'number') attributes[f.name] = parseFloat(v);
        else if (f.type === 'boolean') attributes[f.name] = v === 'true';
        else attributes[f.name] = v;
      }
    });
    try {
      await skusApi.create({
        sku_code: skuCode,
        name,
        item_type_id: itemTypeId,
        attributes,
        reorder_point: reorderPoint ? parseFloat(reorderPoint) : undefined,
        unit_cost: unitCost ? parseFloat(unitCost) : undefined,
      });
      setSkuCode('');
      setName('');
      setAttrs({});
      setReorderPoint('');
      setUnitCost('');
      setShowForm(false);
      refetch();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="page skus">
      <h1>SKUs</h1>
      <p>Manage SKUs with dynamic attributes per item type.</p>
      <div className="filters">
        <input placeholder="Search..." value={search} onChange={e => setSearch(e.target.value)} />
        <select value={itemTypeId} onChange={e => setItemTypeId(e.target.value)}>
          <option value="">All types</option>
          {types.map(t => (
            <option key={t.id} value={t.id}>{t.code}</option>
          ))}
        </select>
      </div>
      <button onClick={() => setShowForm(!showForm)}>
        {showForm ? 'Cancel' : '+ New SKU'}
      </button>

      {showForm && (
        <form onSubmit={handleCreate} className="card form">
          <h2>Create SKU</h2>
          <label>
            Item Type <select value={itemTypeId} onChange={e => { setItemTypeId(e.target.value); setAttrs({}); }} required>
              <option value="">Select...</option>
              {types.map(t => (
                <option key={t.id} value={t.id}>{t.name} ({t.code})</option>
              ))}
            </select>
          </label>
          <label>
            SKU Code <input value={skuCode} onChange={e => setSkuCode(e.target.value)} required />
          </label>
          <label>
            Name <input value={name} onChange={e => setName(e.target.value)} required />
          </label>
          {schema.length > 0 && (
            <>
              <h3>Attributes</h3>
              {schema.map(f => (
                <label key={f.name}>
                  {f.name} ({f.type}){f.required ? '*' : ''}
                  {f.type === 'text' && <input value={attrs[f.name] ?? ''} onChange={e => setAttrs({ ...attrs, [f.name]: e.target.value })} />}
                  {f.type === 'number' && <input type="number" value={attrs[f.name] ?? ''} onChange={e => setAttrs({ ...attrs, [f.name]: e.target.value })} />}
                  {f.type === 'date' && <input type="date" value={attrs[f.name] ?? ''} onChange={e => setAttrs({ ...attrs, [f.name]: e.target.value })} />}
                  {f.type === 'boolean' && <select value={attrs[f.name] ?? ''} onChange={e => setAttrs({ ...attrs, [f.name]: e.target.value })}><option value="">-</option><option value="true">Yes</option><option value="false">No</option></select>}
                  {f.type === 'enum' && <select value={attrs[f.name] ?? ''} onChange={e => setAttrs({ ...attrs, [f.name]: e.target.value })}><option value="">-</option>{(f.options ?? []).map(o => <option key={o} value={o}>{o}</option>)}</select>}
                </label>
              ))}
            </>
          )}
          <label>
            Reorder Point <input type="number" value={reorderPoint} onChange={e => setReorderPoint(e.target.value)} />
          </label>
          <label>
            Unit Cost <input type="number" step="0.01" value={unitCost} onChange={e => setUnitCost(e.target.value)} />
          </label>
          <button type="submit">Create</button>
        </form>
      )}

      <table className="table">
        <thead>
          <tr>
            <th>SKU Code</th>
            <th>Name</th>
            <th>Type</th>
            <th>Reorder</th>
            <th>Cost</th>
          </tr>
        </thead>
        <tbody>
          {skus.map(s => (
            <tr key={s.id}>
              <td>{s.sku_code}</td>
              <td>{s.name}</td>
              <td>{types.find(t => t.id === s.item_type_id)?.code ?? s.item_type_id}</td>
              <td>{s.reorder_point ?? '-'}</td>
              <td>{s.unit_cost ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
