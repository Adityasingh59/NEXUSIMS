/**
 * NEXUS IMS — Accept Invitation page (Block 4)
 * Route: /accept-invitation?token=<raw_token>
 */
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { acceptInvitation } from "../api/users";

export default function AcceptInvitation() {
    const [searchParams] = useSearchParams();
    const token = searchParams.get("token") ?? "";
    const navigate = useNavigate();

    const [fullName, setFullName] = useState("");
    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [done, setDone] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (password !== confirm) {
            setError("Passwords do not match");
            return;
        }
        setLoading(true);
        setError(null);
        try {
            await acceptInvitation({ token, password, full_name: fullName || undefined });
            setDone(true);
            setTimeout(() => navigate("/"), 2000);
        } catch (err: unknown) {
            const msg =
                (err as { response?: { data?: { detail?: string } } })?.response?.data
                    ?.detail ?? "Failed to accept invitation";
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    if (!token) {
        return (
            <div className="invitation-container">
                <div className="invitation-card">
                    <h2>Invalid Invitation</h2>
                    <p>No invitation token found. Please use the link from your email.</p>
                </div>
            </div>
        );
    }

    if (done) {
        return (
            <div className="invitation-container">
                <div className="invitation-card success">
                    <h2>✓ Account Created!</h2>
                    <p>Your account has been created. Redirecting to login…</p>
                </div>
            </div>
        );
    }

    return (
        <div className="invitation-container">
            <div className="invitation-card">
                <div className="invitation-header">
                    <div className="invitation-logo">NEXUS IMS</div>
                    <h2>Set Up Your Account</h2>
                    <p>You've been invited to join NEXUS IMS. Create your password to get started.</p>
                </div>

                {error && <div className="error-banner">{error}</div>}

                <form onSubmit={handleSubmit} className="invitation-form">
                    <div className="form-group">
                        <label>Full Name (optional)</label>
                        <input
                            type="text"
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                            placeholder="Your full name"
                        />
                    </div>
                    <div className="form-group">
                        <label>Password *</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Choose a strong password"
                            required
                            minLength={8}
                        />
                    </div>
                    <div className="form-group">
                        <label>Confirm Password *</label>
                        <input
                            type="password"
                            value={confirm}
                            onChange={(e) => setConfirm(e.target.value)}
                            placeholder="Repeat your password"
                            required
                        />
                    </div>
                    <button type="submit" disabled={loading} className="btn-primary">
                        {loading ? "Creating account…" : "Create Account"}
                    </button>
                </form>
            </div>
        </div>
    );
}
