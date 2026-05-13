import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../lib/api';
import { useToast } from '../lib/toast';

interface WorkflowAction {
  action_type: string;
  action_config: Record<string, unknown>;
}

interface Workflow {
  id: string;
  name: string;
  trigger_type: string;
  trigger_config: Record<string, unknown>;
  is_active: boolean;
  actions: WorkflowAction[];
  created_at: string;
}

interface Execution {
  id: string;
  status: string;
  started_at: string | null;
  error_message: string | null;
}

const TRIGGER_TYPES = [
  'RECEIVE', 'PICK', 'ADJUST', 'RETURN',
  'TRANSFER_OUT', 'TRANSFER_IN', 'COUNT_CORRECT',
  'WRITE_OFF', 'ASSEMBLE_OUT', 'ASSEMBLE_IN',
  'SHIP_OUT', 'RESERVE_OUT', 'RESERVE_IN',
];

const ACTION_TYPES = ['send_webhook', 'send_email', 'create_purchase_order', 'log_event'];

function defaultTriggerConfig() {
  return { operator: 'AND', conditions: [{ field: 'quantity', operator: 'less_than', value: 10 }] };
}

export function Workflows() {
  const toast = useToast();
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<Workflow | null>(null);

  const [name, setName] = useState('');
  const [triggerType, setTriggerType] = useState(TRIGGER_TYPES[0]);
  const [triggerConfig, setTriggerConfig] = useState(JSON.stringify(defaultTriggerConfig(), null, 2));
  const [actions, setActions] = useState([{ action_type: 'send_webhook', action_config: '{"url": "https://example.com/hook"}' }]);
  const [testPayload, setTestPayload] = useState('{"quantity": 5, "sku_id": "...", "warehouse_id": "..."}');
  const [testResult, setTestResult] = useState<Record<string, unknown> | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['workflows'],
    queryFn: () => apiClient.get('/workflows/').then(r => r.data.data as Workflow[]),
  });

  const createMutation = useMutation({
    mutationFn: (payload: unknown) => apiClient.post('/workflows/', payload),
    onSuccess: () => { toast.success('Workflow created'); qc.invalidateQueries({ queryKey: ['workflows'] }); resetForm(); },
    onError: () => toast.error('Failed to create workflow'),
  });

  const { data: executions } = useQuery({
    queryKey: ['workflow-executions', selected?.id],
    queryFn: () => selected
      ? apiClient.get(`/workflows/${selected.id}/executions`).then(r => r.data.data as Execution[])
      : Promise.resolve([]),
    enabled: !!selected,
  });

  const resetForm = () => {
    setName(''); setTriggerType(TRIGGER_TYPES[0]);
    setTriggerConfig(JSON.stringify(defaultTriggerConfig(), null, 2));
    setActions([{ action_type: 'send_webhook', action_config: '{"url": "https://example.com/hook"}' }]);
    setShowCreate(false);
  };

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    let parsedConfig: unknown;
    let parsedActions: unknown[];
    try {
      parsedConfig = JSON.parse(triggerConfig);
      parsedActions = actions.map(a => ({ action_type: a.action_type, action_config: JSON.parse(a.action_config) }));
    } catch {
      toast.error('Invalid JSON in trigger config or action config');
      return;
    }
    createMutation.mutate({ name, trigger_type: triggerType, trigger_config: parsedConfig, actions: parsedActions });
  };

  const handleTest = async (wf: Workflow) => {
    try {
      const payload = JSON.parse(testPayload);
      const r = await apiClient.post(`/workflows/${wf.id}/test`, payload);
      setTestResult(r.data.data as Record<string, unknown>);
      toast.info((r.data.data as { conditions_passed: boolean }).conditions_passed
        ? 'Conditions PASSED — workflow would trigger'
        : 'Conditions did not pass');
    } catch {
      toast.error('Test failed — check payload JSON');
    }
  };

  const workflows = data ?? [];

  return (
    <div className="page">
      <div className="page-header">
        <h1>Workflows</h1>
        <p>Automate actions triggered by stock events. Conditions are evaluated on every ledger write.</p>
        <div className="page-actions">
          <button onClick={() => { resetForm(); setShowCreate(true); }}>+ New Workflow</button>
        </div>
      </div>

      {showCreate && (
        <div className="modal-backdrop" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 640 }}>
            <div className="modal-header">
              <h2>New Workflow</h2>
              <button className="modal-close" onClick={() => setShowCreate(false)}>✕</button>
            </div>
            <form onSubmit={handleCreate}>
              <label>Workflow Name
                <input value={name} onChange={e => setName(e.target.value)} required placeholder="Low stock alert" />
              </label>
              <label style={{ marginTop: '0.75rem', display: 'block' }}>Trigger Event Type
                <select value={triggerType} onChange={e => setTriggerType(e.target.value)}>
                  {TRIGGER_TYPES.map(t => <option key={t}>{t}</option>)}
                </select>
              </label>
              <label style={{ marginTop: '0.75rem', display: 'block' }}>Trigger Conditions (JSON)
                <textarea value={triggerConfig} onChange={e => setTriggerConfig(e.target.value)} rows={6}
                  style={{ width: '100%', fontFamily: 'monospace', fontSize: '0.8rem' }} />
              </label>
              <div style={{ marginTop: '0.75rem' }}>
                <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.4rem', color: 'var(--color-mist)' }}>Actions</div>
                {actions.map((a, i) => (
                  <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', marginBottom: '0.5rem' }}>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                      <select value={a.action_type} onChange={e => { const n = [...actions]; n[i].action_type = e.target.value; setActions(n); }}>
                        {ACTION_TYPES.map(t => <option key={t}>{t}</option>)}
                      </select>
                      <button type="button" className="btn-sm btn-danger" onClick={() => setActions(actions.filter((_, idx) => idx !== i))} disabled={actions.length === 1}>Remove</button>
                    </div>
                    <textarea value={a.action_config} onChange={e => { const n = [...actions]; n[i].action_config = e.target.value; setActions(n); }}
                      rows={2} style={{ width: '100%', fontFamily: 'monospace', fontSize: '0.75rem' }} placeholder='{"url": "https://..."}' />
                  </div>
                ))}
                <button type="button" className="outline btn-sm" onClick={() => setActions([...actions, { action_type: 'send_webhook', action_config: '{}' }])}>+ Add Action</button>
              </div>
              <div className="modal-footer">
                <button type="button" className="outline" onClick={() => setShowCreate(false)}>Cancel</button>
                <button type="submit" disabled={createMutation.isPending}>{createMutation.isPending ? 'Creating…' : 'Create Workflow'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {selected && (
        <div className="modal-backdrop" onClick={() => { setSelected(null); setTestResult(null); }}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 700 }}>
            <div className="modal-header">
              <h2>{selected.name} — Detail</h2>
              <button className="modal-close" onClick={() => { setSelected(null); setTestResult(null); }}>✕</button>
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--color-mist)', marginBottom: '0.5rem' }}>Trigger: <strong>{selected.trigger_type}</strong></div>
              <pre style={{ background: 'var(--color-surface-2)', padding: '0.75rem', borderRadius: 6, fontSize: '0.75rem', overflowX: 'auto' }}>
                {JSON.stringify(selected.trigger_config, null, 2)}
              </pre>
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.4rem' }}>Actions ({selected.actions?.length ?? 0})</div>
              {(selected.actions ?? []).map((a, i) => (
                <div key={i} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontSize: '0.8rem', padding: '0.35rem 0', borderBottom: '1px solid var(--color-edge)' }}>
                  <span className="badge badge-info">{a.action_type}</span>
                  <span className="mono" style={{ color: 'var(--color-mist)', fontSize: '0.75rem' }}>{JSON.stringify(a.action_config)}</span>
                </div>
              ))}
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.4rem' }}>Test Trigger</div>
              <textarea value={testPayload} onChange={e => setTestPayload(e.target.value)} rows={3}
                style={{ width: '100%', fontFamily: 'monospace', fontSize: '0.8rem', marginBottom: '0.5rem' }} />
              <button type="button" className="secondary" onClick={() => handleTest(selected)}>Run Test</button>
              {testResult && (
                <pre style={{ marginTop: '0.5rem', background: 'var(--color-surface-2)', padding: '0.75rem', borderRadius: 6, fontSize: '0.75rem' }}>
                  {JSON.stringify(testResult, null, 2)}
                </pre>
              )}
            </div>
            <div style={{ marginTop: '1.25rem' }}>
              <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.4rem' }}>Execution History</div>
              {!executions || executions.length === 0
                ? <div className="empty-state" style={{ padding: '1rem 0' }}><h3>No executions yet</h3></div>
                : executions.slice(0, 10).map(ex => (
                  <div key={ex.id} style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', padding: '0.4rem 0', borderBottom: '1px solid var(--color-edge)', fontSize: '0.8rem' }}>
                    <span className={`badge ${ex.status === 'SUCCESS' ? 'badge-received' : 'badge-danger'}`}>{ex.status}</span>
                    <span className="text-muted">{ex.started_at ? new Date(ex.started_at).toLocaleString() : '—'}</span>
                    {ex.error_message && <span style={{ color: 'var(--color-red)', fontSize: '0.75rem' }}>{ex.error_message}</span>}
                  </div>
                ))
              }
            </div>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="loading">Loading workflows</div>
      ) : workflows.length === 0 ? (
        <div className="empty-state card">
          <h3>No workflows configured</h3>
          <p>Create a workflow to automate actions on stock events.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Name</th><th>Trigger</th><th>Actions</th><th>Status</th><th>Created</th><th></th></tr></thead>
            <tbody>
              {workflows.map(wf => (
                <tr key={wf.id}>
                  <td><strong>{wf.name}</strong></td>
                  <td><span className="badge badge-info">{wf.trigger_type}</span></td>
                  <td>{wf.actions?.length ?? 0} action{wf.actions?.length !== 1 ? 's' : ''}</td>
                  <td><span className={`badge ${wf.is_active ? 'badge-received' : 'badge-inactive'}`}>{wf.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td className="text-muted">{wf.created_at ? new Date(wf.created_at).toLocaleDateString() : '—'}</td>
                  <td><button className="btn-sm secondary" onClick={() => setSelected(wf)}>View</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
