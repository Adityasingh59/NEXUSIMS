import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { locationsApi, type Location } from '../api/locations';
import { warehousesApi, type Warehouse } from '../api/warehouses';

export function Locations() {
  const [warehouseId, setWarehouseId] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [locationType, setLocationType] = useState<'ZONE' | 'AISLE' | 'BIN'>('ZONE');
  const [parentId, setParentId] = useState('');

  const { data: whData } = useQuery({
    queryKey: ['warehouses'],
    queryFn: async () => {
      const r = await warehousesApi.list();
      return r.data?.data ?? [];
    },
  });

  const { data, refetch } = useQuery({
    queryKey: ['locations', warehouseId],
    queryFn: async () => {
      const r = await locationsApi.list(warehouseId);
      return r.data?.data ?? [];
    },
    enabled: !!warehouseId,
  });

  const warehouses = (whData ?? []) as Warehouse[];
  const locations = (data ?? []) as Location[];

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await locationsApi.create({
        warehouse_id: warehouseId,
        name,
        code,
        location_type: locationType,
        parent_id: parentId || undefined,
      });
      setName('');
      setCode('');
      setShowForm(false);
      refetch();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="page locations">
      <h1>Locations</h1>
      <p>Zone &gt; Aisle &gt; Bin hierarchy per warehouse.</p>
      <label>
        Warehouse <select value={warehouseId} onChange={e => setWarehouseId(e.target.value)}>
          <option value="">Select...</option>
          {warehouses.map(w => <option key={w.id} value={w.id}>{w.code} – {w.name}</option>)}
        </select>
      </label>

      {warehouseId && (
        <>
          <button onClick={() => setShowForm(!showForm)}>{showForm ? 'Cancel' : '+ New Location'}</button>
          {showForm && (
            <form onSubmit={handleCreate} className="form">
              <h2>Create Location</h2>
              <label>Name <input value={name} onChange={e => setName(e.target.value)} required /></label>
              <label>Code <input value={code} onChange={e => setCode(e.target.value)} placeholder="e.g. A-01" required /></label>
              <label>Type <select value={locationType} onChange={e => setLocationType(e.target.value as 'ZONE' | 'AISLE' | 'BIN')}>
                <option value="ZONE">Zone</option>
                <option value="AISLE">Aisle</option>
                <option value="BIN">Bin</option>
              </select></label>
              <label>Parent <select value={parentId} onChange={e => setParentId(e.target.value)}>
                <option value="">None (root)</option>
                {locations.map(l => <option key={l.id} value={l.id}>{l.code} ({l.location_type})</option>)}
              </select></label>
              <button type="submit">Create</button>
            </form>
          )}
          <table className="table">
            <thead>
              <tr><th>Code</th><th>Name</th><th>Type</th><th>Parent</th></tr>
            </thead>
            <tbody>
              {locations.map(l => (
                <tr key={l.id}>
                  <td>{l.code}</td>
                  <td>{l.name}</td>
                  <td>{l.location_type}</td>
                  <td>{locations.find(p => p.id === l.parent_id)?.code ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
