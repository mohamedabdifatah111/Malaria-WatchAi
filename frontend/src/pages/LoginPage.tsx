import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { toApiError } from "../api/client";
import { Notice } from "../components/ui";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login, isAuthenticated, sessionExpired } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/dashboard";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (isAuthenticated) return <Navigate to={from} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError("Enter your username and password.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      const apiErr = toApiError(err);
      setError(apiErr.status === 400
        ? "Those credentials were not accepted. Check your username and password."
        : apiErr.status === 429 ? "Too many sign-in attempts. Wait a minute and try again." : apiErr.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center bg-navy-900 px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-semibold text-white">MalariaWatchAI</h1>
          <p className="mt-1 text-sm text-white/65">Malaria surveillance and geospatial decision support</p>
        </div>
        <form onSubmit={submit} noValidate className="space-y-4 rounded-lg bg-white p-6 shadow-lg">
          {sessionExpired && <Notice tone="warning">Your session has ended. Sign in again to continue.</Notice>}
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-ink">Username</label>
            <input id="username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)}
              className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm focus:border-teal-600" />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-ink">Password</label>
            <input id="password" type="password" autoComplete="current-password" value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm focus:border-teal-600" />
          </div>
          {error && <p role="alert" className="text-sm text-crit-700">{error}</p>}
          <button type="submit" disabled={busy}
            className="w-full rounded-md bg-teal-700 px-3 py-2 text-sm font-medium text-white hover:bg-teal-600 disabled:opacity-60">
            {busy ? "Signing in..." : "Sign in"}
          </button>
          <p className="text-center text-xs text-ink-3">Accounts are issued by the project administrators.</p>
        </form>
        <p className="mt-4 text-center text-xs text-white/50">For surveillance and planning. Not for diagnosis or treatment.</p>
      </div>
    </div>
  );
}
