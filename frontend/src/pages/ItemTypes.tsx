import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { itemTypesApi, type AttributeFieldSchema, type ItemType } from '../api/itemTypes';

export function ItemTypes() {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [schema, setSchema] = useState<AttributeFieldSchema[]>([]);

  const { data, refetch } = useQuery({
    queryKey: ['item-types'],
    queryFn: async () => {
      const r = await itemTypesApi.list();
      return r.data?.data ?? [];
    },
  });

  const addField = () => {
    setSchema([...schema, { name: '', type: 'text', required: false }]);
  };

  const removeField = (i: number) => {
    setSchema(schema.filter((_, idx) => idx !== i));
  };

  const updateField = (i: number, key: keyof AttributeFieldSchema, value: unknown) => {
    const next = [...schema];
    (next[i] as unknown as Record<string, unknown>)[key] = value;
    setSchema(next);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const validSchema = schema.filter(f => f.name.trim());
    try {
      await itemTypesApi.create({ name, code, attribute_schema: validSchema });
      setName('');
      setCode('');
      setSchema([]);
      setShowForm(false);
      refetch();
    } catch (err) {
      console.error(err);
    }
  };

  const types = (data ?? []) as ItemType[];

  return (
    <div className="page item-types">
      <h1>Item Types</h1>
      <p>Define polymorphic item types with custom attribute schemas.</p>
      <button onClick={() => setShowForm(!showForm)}>
        {showForm ? 'Cancel' : '+ New Item Type'}
      </button>

      {showForm && (
        <form onSubmit={handleCreate} className="card form">
          <h2>Create Item Type</h2>
          <label>
            Name <input value={name} onChange={e => setName(e.target.value)} required />
          </label>
          <label>
            Code <input value={code} onChange={e => setCode(e.target.value)} placeholder="e.g. RING" required />
          </label>
          <h3>Attribute Schema</h3>
          {schema.map((f, i) => (
            <div key={i} className="schema-row">
              <input
                placeholder="field name"
                value={f.name}
                onChange={e => updateField(i, 'name', e.target.value)}
              />
              <select value={f.type} onChange={e => updateField(i, 'type', e.target.value)}>
                <option value="text">text</option>
                <option value="number">number</option>
                <option value="date">date</option>
                <option value="boolean">boolean</option>
                <option value="enum">enum</option>
              </select>
              <label>
                <input type="checkbox" checked={!!f.required} onChange={e => updateField(i, 'required', e.target.checked)} />
                required
              </label>
              <button type="button" onClick={() => removeField(i)}>Remove</button>
            </div>
          ))}
          <button type="button" onClick={addField}>+ Add Field</button>
          <button type="submit">Create</button>
        </form>
      )}

      <table className="table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Name</th>
            <th>Version</th>
            <th>Fields</th>
          </tr>
        </thead>
        <tbody>
          {types.map(t => (
            <tr key={t.id}>
              <td>{t.code}</td>
              <td>{t.name}</td>
              <td>{t.version}</td>
              <td>{(t.attribute_schema ?? []).length}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
