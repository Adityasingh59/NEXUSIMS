import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { warehousesApi } from '../api/warehouses';
import type { Warehouse } from '../api/warehouses';

export function Warehouses() {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [address, setAddress] = useState('');

  const { data, refetch } = useQuery({
    queryKey: ['warehouses'],
    queryFn: async () => {
      const r = await warehousesApi.list();
      return r.data?.data ?? [];
    },
  });

  const warehouses = (data ?? []) as Warehouse[];

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await warehousesApi.create({ name, code, address: address || undefined });
      setName('');
      setCode('');
      setAddress('');
      setShowForm(false);
      refetch();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="page warehouses">
      <h1>Warehouses</h1>
      <p>Create warehouses for stock ledger. Block 3 adds locations and transfers.</p>
      <button onClick={() => setShowForm(!showForm)}>
        {showForm ? 'Cancel' : '+ New Warehouse'}
      </button>

      {showForm && (
        <form onSubmit={handleCreate} className="form">
          <h2>Create Warehouse</h2>
          <label>Name <input value={name} onChange={e => setName(e.target.value)} required /></label>
          <label>Code <input value={code} onChange={e => setCode(e.target.value)} placeholder="e.g. WH1" required /></label>
          <label>Address <input value={address} onChange={e => setAddress(e.target.value)} /></label>
          <button type="submit">Create</button>
        </form>
      )}

      <table className="table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Name</th>
            <th>Address</th>
          </tr>
        </thead>
        <tbody>
          {warehouses.map(w => (
            <tr key={w.id}>
              <td>{w.code}</td>
              <td>{w.name}</td>
              <td>{w.address ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
