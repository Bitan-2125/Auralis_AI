import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/chat");
    } catch (err) {
      setError(err?.response?.data?.detail || "Couldn't sign in. Check your details.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-ink px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-2 mb-2">
            <span className="w-2 h-2 rounded-full bg-signal"></span>
            <span className="font-mono text-xs tracking-widest text-muted uppercase">Auralis AI</span>
          </div>
          <h1 className="font-display text-2xl font-semibold">Sign in</h1>
        </div>

        <form onSubmit={handleSubmit} className="bg-panel border border-line rounded-lg p-6 space-y-4">
          {error && (
            <div className="text-sm text-red-400 bg-red-950/40 border border-red-900 rounded-sm px-3 py-2">
              {error}
            </div>
          )}
          <div>
            <label className="block text-xs text-muted mb-1 font-mono">Email</label>
            <input
              type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-panel2 border border-line rounded-sm px-3 py-2 text-sm focus:border-accent outline-none"
              placeholder="you@company.com"
            />
          </div>
          <div>
            <label className="block text-xs text-muted mb-1 font-mono">Password</label>
            <input
              type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-panel2 border border-line rounded-sm px-3 py-2 text-sm focus:border-accent outline-none"
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit" disabled={loading}
            className="w-full bg-accent hover:bg-accent/90 disabled:opacity-50 text-white text-sm font-medium rounded-sm py-2 transition-colors"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="text-center text-sm text-muted mt-4">
          No account? <Link to="/register" className="text-accent hover:underline">Create one</Link>
        </p>
      </div>
    </div>
  );
}
