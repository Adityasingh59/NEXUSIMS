/**
 * NEXUS IMS — Users Management page (Block 4)
 * Only accessible to ADMIN role.
 */
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    listUsers,
    inviteUser,
    updateUserRole,
    deactivateUser,
    type UserResponse, // Type import
} from "../api/users";

const ROLES = ["ADMIN", "MANAGER", "FLOOR_ASSOCIATE"];

export function Users() {
    const qc = useQueryClient();
    const { data: users = [], isLoading } = useQuery({
        queryKey: ["users"],
        queryFn: () => listUsers(),
    });

    // Invite modal state
    const [showInvite, setShowInvite] = useState(false);
    const [inviteEmail, setInviteEmail] = useState("");
    const [inviteRole, setInviteRole] = useState("FLOOR_ASSOCIATE");
    const [devToken, setDevToken] = useState<string | null>(null);

    // Role edit state
    const [editingUser, setEditingUser] = useState<UserResponse | null>(null);
    const [editRole, setEditRole] = useState("");

    const inviteMutation = useMutation({
        mutationFn: inviteUser,
        onSuccess: (data) => {
            qc.invalidateQueries({ queryKey: ["users"] });
            setDevToken(data.dev_token);
            setInviteEmail("");
            setInviteRole("FLOOR_ASSOCIATE");
        },
    });

    const roleMutation = useMutation({
        mutationFn: ({ id, role }: { id: string; role: string }) =>
            updateUserRole(id, { role }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["users"] });
            setEditingUser(null);
        },
    });

    const deactivateMutation = useMutation({
        mutationFn: deactivateUser,
        onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
    });

    const roleColors: Record<string, string> = {
        ADMIN: "#7c3aed",
        MANAGER: "#0891b2",
        FLOOR_ASSOCIATE: "#059669",
    };

    return (
        <div className="page-container">
            <div className="page-header">
                <div>
                    <h1 className="page-title">User Management</h1>
                    <p className="page-subtitle">
                        Manage team members and their access roles
                    </p>
                </div>
                <button
                    className="btn-primary"
                    onClick={() => { setShowInvite(true); setDevToken(null); }}
                >
                    + Invite User
                </button>
            </div>

            {/* Invite Modal */}
            {showInvite && (
                <div className="modal-overlay" onClick={() => setShowInvite(false)}>
                    <div className="modal-box" onClick={(e) => e.stopPropagation()}>
                        <h3 className="modal-title">Invite New User</h3>
                        {devToken ? (
                            <div>
                                <p style={{ color: "var(--success)" }}>✓ Invitation created!</p>
                                <p style={{ fontSize: "0.85rem", opacity: 0.7, margin: "8px 0" }}>
                                    (Dev mode) Invite link:
                                </p>
                                <code className="token-display">
                                    {window.location.origin}/accept-invitation?token={devToken}
                                </code>
                                <button
                                    className="btn-primary"
                                    style={{ marginTop: 16 }}
                                    onClick={() => setShowInvite(false)}
                                >
                                    Done
                                </button>
                            </div>
                        ) : (
                            <form
                                onSubmit={(e) => {
                                    e.preventDefault();
                                    inviteMutation.mutate({ email: inviteEmail, role: inviteRole });
                                }}
                            >
                                <div className="form-group">
                                    <label>Email</label>
                                    <input
                                        type="email"
                                        value={inviteEmail}
                                        onChange={(e) => setInviteEmail(e.target.value)}
                                        required
                                        placeholder="user@company.com"
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Role</label>
                                    <select
                                        value={inviteRole}
                                        onChange={(e) => setInviteRole(e.target.value)}
                                    >
                                        {ROLES.map((r) => (
                                            <option key={r} value={r}>{r}</option>
                                        ))}
                                    </select>
                                </div>
                                {inviteMutation.error && (
                                    <p style={{ color: "var(--error)", fontSize: "0.85rem" }}>
                                        {(inviteMutation.error as Error).message}
                                    </p>
                                )}
                                <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                                    <button
                                        type="button"
                                        className="btn-secondary"
                                        onClick={() => setShowInvite(false)}
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        className="btn-primary"
                                        disabled={inviteMutation.isPending}
                                    >
                                        {inviteMutation.isPending ? "Sending…" : "Send Invitation"}
                                    </button>
                                </div>
                            </form>
                        )}
                    </div>
                </div>
            )}

            {/* Edit Role Modal */}
            {editingUser && (
                <div className="modal-overlay" onClick={() => setEditingUser(null)}>
                    <div className="modal-box" onClick={(e) => e.stopPropagation()}>
                        <h3 className="modal-title">Change Role</h3>
                        <p style={{ opacity: 0.7, marginBottom: 16 }}>{editingUser.email}</p>
                        <div className="form-group">
                            <label>New Role</label>
                            <select value={editRole} onChange={(e) => setEditRole(e.target.value)}>
                                {ROLES.map((r) => (
                                    <option key={r} value={r}>{r}</option>
                                ))}
                            </select>
                        </div>
                        <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                            <button className="btn-secondary" onClick={() => setEditingUser(null)}>
                                Cancel
                            </button>
                            <button
                                className="btn-primary"
                                onClick={() =>
                                    roleMutation.mutate({ id: editingUser.id, role: editRole })
                                }
                                disabled={roleMutation.isPending}
                            >
                                {roleMutation.isPending ? "Saving…" : "Save"}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Users Table */}
            <div className="card">
                {isLoading ? (
                    <div className="loading-state">Loading users…</div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>User</th>
                                <th>Role</th>
                                <th>Status</th>
                                <th>Warehouse Scope</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {users.map((u) => (
                                <tr key={u.id}>
                                    <td>
                                        <div className="user-cell">
                                            <div className="user-avatar">
                                                {(u.full_name ?? u.email)[0].toUpperCase()}
                                            </div>
                                            <div>
                                                <div className="user-name">{u.full_name ?? "—"}</div>
                                                <div className="user-email">{u.email}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td>
                                        <span
                                            className="role-badge"
                                            style={{
                                                background: `${roleColors[u.role] ?? "#666"}22`,
                                                color: roleColors[u.role] ?? "#666",
                                                borderColor: `${roleColors[u.role] ?? "#666"}44`,
                                            }}
                                        >
                                            {u.role}
                                        </span>
                                    </td>
                                    <td>
                                        <span className={`status-dot ${u.is_active ? "active" : "inactive"}`}>
                                            {u.is_active ? "Active" : "Inactive"}
                                        </span>
                                    </td>
                                    <td>
                                        {u.warehouse_scope
                                            ? `${u.warehouse_scope.length} warehouse(s)`
                                            : "All warehouses"}
                                    </td>
                                    <td>
                                        <div className="action-buttons">
                                            <button
                                                className="btn-sm btn-secondary"
                                                onClick={() => {
                                                    setEditingUser(u);
                                                    setEditRole(u.role);
                                                }}
                                            >
                                                Change Role
                                            </button>
                                            {u.is_active && (
                                                <button
                                                    className="btn-sm btn-danger"
                                                    onClick={() => {
                                                        if (
                                                            window.confirm(
                                                                `Deactivate ${u.email}? They will lose access immediately.`
                                                            )
                                                        ) {
                                                            deactivateMutation.mutate(u.id);
                                                        }
                                                    }}
                                                >
                                                    Deactivate
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {users.length === 0 && (
                                <tr>
                                    <td colSpan={5} className="empty-state">
                                        No users found. Invite your first team member!
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
