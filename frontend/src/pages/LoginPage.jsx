import { useState } from "react";
import { Navigate } from "react-router-dom";
import { AlertCircle, Lock, Mail, ScrollText, ShieldHalf, Sparkles, Timer } from "lucide-react";
import { useAuth } from "../lib/auth";

const HERO_POINTS = [
  { icon: Timer, text: "Transactions scored and decided in real time" },
  { icon: Sparkles, text: "Every decision explained in plain language by an LLM" },
  { icon: ScrollText, text: "Full audit trail behind each allow, escalate, or block" },
];

export default function LoginPage() {
  const { session, signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  if (session) return <Navigate to="/queue" replace />;

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const { error: signInError } = await signIn(email, password);
    setLoading(false);
    if (signInError) setError(signInError.message);
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-hero">
          <div className="login-hero-brand">
            <ShieldHalf size={18} />
            Solaris
          </div>
          <div className="login-hero-content">
            <h2>Catch fraud as it happens, not after the fact.</h2>
            <p>
              A six-step reasoning pipeline scores, explains, and logs every transaction
              so your team reviews decisions instead of raw data.
            </p>
            <div className="login-hero-points">
              {HERO_POINTS.map(({ icon: Icon, text }) => (
                <div className="login-hero-point" key={text}>
                  <Icon />
                  {text}
                </div>
              ))}
            </div>
          </div>
          <div className="login-hero-foot">Solaris — built for the Synchrony hackathon</div>
        </div>
        <div className="login-form-panel">
          <div className="login-shell">
            <div className="login-mark">
              <ShieldHalf size={16} />
            </div>
            <h1>Welcome back</h1>
            <p>Sign in with your analyst or admin account to access the risk queue.</p>
            {error && (
              <div className="error-banner">
                <AlertCircle />
                {error}
              </div>
            )}
            <form onSubmit={handleSubmit}>
              <div className="field">
                <label htmlFor="email">Email</label>
                <div className="input-icon-wrap">
                  <Mail />
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoFocus
                  />
                </div>
              </div>
              <div className="field">
                <label htmlFor="password">Password</label>
                <div className="input-icon-wrap">
                  <Lock />
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>
              </div>
              <button className="btn btn-block" type="submit" disabled={loading}>
                {loading && <span className="spinner" />}
                {loading ? "Signing in…" : "Sign in"}
              </button>
            </form>
            <div className="login-hint">
              Test accounts: <code>test-analyst@synchrony-fraud-agent.local</code> or{" "}
              <code>test-admin@synchrony-fraud-agent.local</code>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
