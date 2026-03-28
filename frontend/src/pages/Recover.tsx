import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api from "../api";
import { KeyRound, Loader2, AlertCircle, CheckCircle2, Copy } from "lucide-react";

export default function Recover() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [recoveryCode, setRecoveryCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [newCode, setNewCode] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/api/auth/recover", {
        username,
        recovery_code: recoveryCode,
        new_password: newPassword,
      });
      localStorage.setItem("scout_token", data.token);
      setNewCode(data.new_recovery_code);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Recovery failed — check your recovery code.");
    } finally {
      setLoading(false);
    }
  }

  if (newCode) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
        <div className="w-full max-w-sm space-y-5">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-emerald-600/20 border border-emerald-500/30 mb-4">
              <CheckCircle2 size={26} className="text-emerald-400" />
            </div>
            <h1 className="text-2xl font-bold text-white">Password reset!</h1>
          </div>

          <div className="bg-amber-950/40 border border-amber-700/50 rounded-xl p-4 space-y-3">
            <p className="text-xs text-amber-300 font-medium">
              A new recovery code has been generated. Save it!
            </p>
            <div className="flex items-center gap-2 bg-gray-900 rounded-lg px-3 py-2.5">
              <code className="flex-1 text-sm font-mono text-emerald-300 tracking-wider break-all">
                {newCode}
              </code>
              <button
                onClick={() => { navigator.clipboard.writeText(newCode); setCopied(true); }}
                className="text-gray-400 hover:text-white shrink-0"
              >
                {copied ? <CheckCircle2 size={14} className="text-emerald-400" /> : <Copy size={14} />}
              </button>
            </div>
          </div>

          <button
            onClick={() => navigate("/", { replace: true })}
            className="w-full bg-indigo-600 hover:bg-indigo-500 py-2.5 rounded-lg text-sm font-medium"
          >
            Go to Scout
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
            <KeyRound size={26} className="text-indigo-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">Recover account</h1>
          <p className="text-sm text-gray-500 mt-1">Use your recovery code to reset your password</p>
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
                autoFocus
                className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-indigo-500"
                placeholder="your username"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">Recovery code</label>
              <input
                type="text"
                value={recoveryCode}
                onChange={(e) => setRecoveryCode(e.target.value)}
                required
                className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2.5 text-sm font-mono outline-none focus:border-indigo-500"
                placeholder="paste your recovery code"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">New password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={6}
                className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-indigo-500"
                placeholder="new password"
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
            disabled={loading || !username || !recoveryCode || !newPassword}
            className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 py-2.5 rounded-lg text-sm font-medium"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : null}
            {loading ? "Resetting…" : "Reset password"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-600">
          <Link to="/login" className="text-indigo-400 hover:text-indigo-300">
            Back to login
          </Link>
        </p>
      </div>
    </div>
  );
}
