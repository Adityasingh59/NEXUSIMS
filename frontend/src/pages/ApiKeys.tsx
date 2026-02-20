/**
 * NEXUS IMS — API Keys management page (Block 4)
 * Only accessible to ADMIN role.
 */
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { createAPIKey, listAPIKeys, revokeAPIKey, type CreateAPIKeyResponse } from "../api/apiKeys";

const AVAILABLE_SCOPES = [
    "skus:read",
    "skus:write",
    "transactions:receive",
    "transactions:pick",
    "transactions:adjust",
    "warehouses:manage",
    "reports:read",
];

export function ApiKeys() {
    const qc = useQueryClient();
    const { data: keys = [], isLoading } = useQuery({
        queryKey: ["apiKeys"],
        queryFn: listAPIKeys,
    });

    const [showCreate, setShowCreate] = useState(false);
    const [keyName, setKeyName] = useState("");
    const [selectedScopes, setSelectedScopes] = useState<string[]>([]);
    const [createdKey, setCreatedKey] = useState<CreateAPIKeyResponse | null>(null);
    const [copied, setCopied] = useState(false);

    const createMutation = useMutation({
        mutationFn: createAPIKey,
        onSuccess: (data) => {
            qc.invalidateQueries({ queryKey: ["apiKeys"] });
            setCreatedKey(data);
            setKeyName("");
            setSelectedScopes([]);
        },
    });

    const revokeMutation = useMutation({
        mutationFn: revokeAPIKey,
        onSuccess: () => qc.invalidateQueries({ queryKey: ["apiKeys"] }),
    });

    const toggleScope = (scope: string) => {
        setSelectedScopes((prev) =>
            prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope]
        );
    };

    const copyKey = () => {
        if (createdKey) {
            navigator.clipboard.writeText(createdKey.raw_key);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    return (
        <div className="page-container">
            <div className="page-header">
                <div>
                    <h1 className="page-title">API Keys</h1>
                    <p className="page-subtitle">
                        Manage machine-to-machine authentication keys
                    </p>
                </div>
                <button
                    className="btn-primary"
                    onClick={() => { setShowCreate(true); setCreatedKey(null); }}
                >
                    + Create API Key
                </button>
            </div>

            {/* Create Key Modal */}
            {showCreate && (
                <div className="modal-overlay" onClick={() => { setShowCreate(false); setCreatedKey(null); }}>
                    <div className="modal-box wide" onClick={(e) => e.stopPropagation()}>
                        {createdKey ? (
                            <>
                                <h3 className="modal-title">✓ API Key Created</h3>
                                <div className="warning-banner">
                                    ⚠ Copy this key now. It will <strong>never be shown again</strong>.
                                </div>
                                <div className="token-display">
                                    <code>{createdKey.raw_key}</code>
                                </div>
                                <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                                    <button className="btn-primary" onClick={copyKey}>
                                        {copied ? "✓ Copied!" : "Copy Key"}
                                    </button>
                                    <button
                                        className="btn-secondary"
                                        onClick={() => { setShowCreate(false); setCreatedKey(null); }}
                                    >
                                        Done
                                    </button>
                                </div>
                            </>
                        ) : (
                            <>
                                <h3 className="modal-title">Create API Key</h3>
                                <form
                                    onSubmit={(e) => {
                                        e.preventDefault();
                                        createMutation.mutate({ name: keyName, scopes: selectedScopes });
                                    }}
                                >
                                    <div className="form-group">
                                        <label>Key Name</label>
                                        <input
                                            type="text"
                                            value={keyName}
                                            onChange={(e) => setKeyName(e.target.value)}
                                            placeholder="e.g. Webhook integration"
                                            required
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label>Scopes</label>
                                        <div className="scopes-grid">
                                            {AVAILABLE_SCOPES.map((scope) => (
                                                <label key={scope} className="scope-checkbox">
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedScopes.includes(scope)}
                                                        onChange={() => toggleScope(scope)}
                                                    />
                                                    <span>{scope}</span>
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                    <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                                        <button
                                            type="button"
                                            className="btn-secondary"
                                            onClick={() => setShowCreate(false)}
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            type="submit"
                                            className="btn-primary"
                                            disabled={createMutation.isPending}
                                        >
                                            {createMutation.isPending ? "Creating…" : "Create Key"}
                                        </button>
                                    </div>
                                </form>
                            </>
                        )}
                    </div>
                </div>
            )}

            {/* Keys List */}
            <div className="card">
                {isLoading ? (
                    <div className="loading-state">Loading API keys…</div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Key Prefix</th>
                                <th>Scopes</th>
                                <th>Last Used</th>
                                <th>Created</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {keys.map((k) => (
                                <tr key={k.id}>
                                    <td>{k.name}</td>
                                    <td>
                                        <code className="key-prefix">{k.key_prefix}…</code>
                                    </td>
                                    <td>
                                        <div className="scopes-list">
                                            {k.scopes.length > 0
                                                ? k.scopes.map((s) => (
                                                    <span key={s} className="scope-pill">{s}</span>
                                                ))
                                                : <span className="scope-pill all">all</span>}
                                        </div>
                                    </td>
                                    <td>{k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "Never"}</td>
                                    <td>{new Date(k.created_at).toLocaleDateString()}</td>
                                    <td>
                                        <button
                                            className="btn-sm btn-danger"
                                            onClick={() => {
                                                if (
                                                    window.confirm(
                                                        `Revoke key "${k.name}"? This is immediate and irreversible.`
                                                    )
                                                ) {
                                                    revokeMutation.mutate(k.id);
                                                }
                                            }}
                                        >
                                            Revoke
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {keys.length === 0 && (
                                <tr>
                                    <td colSpan={6} className="empty-state">
                                        No API keys yet. Create one for programmatic access.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}
