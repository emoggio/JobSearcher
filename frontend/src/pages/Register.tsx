import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api from "../api";
import { Briefcase, Loader2, AlertCircle, CheckCircle2, Copy } from "lucide-react";

export default function Register() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [recoveryCode, setRecoveryCode] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/api/auth/register", {
        username,
        password,
        confirm_password: confirm,
      });
      localStorage.setItem("scout_token", data.token);
      setRecoveryCode(data.recovery_code);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Registration failed.");
    } finally {
      setLoading(false);
    }
  }

  function copyCode() {
    if (recoveryCode) {
      navigator.clipboard.writeText(recoveryCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  // Recovery code step — shown after successful registration
  if (recoveryCode) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
        <div className="w-full max-w-sm space-y-5">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-emerald-600/20 border border-emerald-500/30 mb-4">
              <CheckCircle2 size={26} className="text-emerald-400" />
            </div>
            <h1 className="text-2xl font-bold text-white">Account created!</h1>
            <p className="text-sm text-gray-500 mt-1">Welcome to Scout</p>
          </div>

          <div className="bg-amber-950/40 border border-amber-700/50 rounded-xl p-4 space-y-3">
            <div className="flex items-start gap-2">
              <AlertCircle size={14} className="text-amber-400 shrink-0 mt-0.5" />
              <p className="text-xs text-amber-300 font-medium">
                Save this recovery code now — it will never be shown again.
                You'll need it to reset your password if you forget it.
              </p>
            </div>
            <div className="flex items-center gap-2 bg-gray-900 rounded-lg px-3 py-2.5">
              <code className="flex-1 text-sm font-mono text-emerald-300 tracking-wider break-all">
                {recoveryCode}
              </code>
              <button
                onClick={copyCode}
                className="text-gray-400 hover:text-white transition-colors shrink-0"
                title="Copy to clipboard"
              >
                {copied ? <CheckCircle2 size={14} className="text-emerald-400" /> : <Copy size={14} />}
              </button>
            </div>
          </div>

          <button
            onClick={() => navigate("/", { replace: true })}
            className="w-full bg-indigo-600 hover:bg-indigo-500 py-2.5 rounded-lg text-sm font-medium transition-colors"
          >
            I've saved it — go to Scout
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 mb-4">
            <Briefcase size={26} className="text-indigo-400" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Create account</h1>
          <p className="text-sm text-gray-500 mt-1">Your personal job search space</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                minLength={3}
                autoFocus
                className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-indigo-500 transition-colors placeholder-gray-700"
                placeholder="choose a username"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-indigo-500 transition-colors placeholder-gray-700"
                placeholder="at least 6 characters"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">Confirm password</label>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-indigo-500 transition-colors placeholder-gray-700"
                placeholder="repeat password"
              />
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-xs text-red-400 bg-red-950/40 border border-red-800/50 rounded-lg px-3 py-2">
              <AlertCircle size={12} className="shrink-0" />
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !username || !password || !confirm}
            className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 py-2.5 rounded-lg text-sm font-medium transition-colors"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : null}
            {loading ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-600">
          Already have an account?{" "}
          <Link to="/login" className="text-indigo-400 hover:text-indigo-300">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
