import { useState, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { getSettings, saveLinkedinCookie } from "../api";
import { Settings2, Eye, EyeOff, Loader2, CheckCircle2, AlertCircle } from "lucide-react";

export default function Settings() {
  const [cookie, setCookie] = useState("");
  const [showCookie, setShowCookie] = useState(false);
  const [saved, setSaved] = useState(false);

  const { data: settings, isLoading: loadingSettings } = useQuery({
    queryKey: ["settings"],
    queryFn: () => getSettings().then((r) => r.data),
    retry: false,
  });

  const { mutate: saveCookie, isPending: saving, isError: saveError } = useMutation({
    mutationFn: () => saveLinkedinCookie(cookie),
    onSuccess: () => {
      setSaved(true);
      setCookie("");
      setTimeout(() => setSaved(false), 3000);
    },
  });

  const hasCookie = settings?.has_linkedin_cookie === true;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="shrink-0 px-4 md:px-6 py-4 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <Settings2 size={16} className="text-indigo-400" />
          <div>
            <h2 className="text-lg font-semibold">Settings</h2>
            <p className="text-xs text-gray-500">Configure Scout integrations and preferences</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto px-4 md:px-6 py-6 space-y-6 max-w-xl">
        {/* LinkedIn Cookie */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              LinkedIn Cookie
            </h3>
            <p className="text-xs text-gray-500 mt-1 leading-relaxed">
              Paste your LinkedIn{" "}
              <code className="bg-gray-800 text-indigo-300 px-1 py-0.5 rounded text-[11px]">li_at</code>{" "}
              session cookie to let Scout scrape jobs as you (bypasses login walls). Find it in browser
              DevTools → Application → Cookies → linkedin.com.
            </p>
          </div>

          {/* Current status */}
          <div className="flex items-center gap-2 text-xs">
            {loadingSettings ? (
              <Loader2 size={12} className="animate-spin text-gray-500" />
            ) : hasCookie ? (
              <>
                <CheckCircle2 size={13} className="text-emerald-400" />
                <span className="text-emerald-400 font-medium">Cookie saved ✓</span>
              </>
            ) : (
              <>
                <AlertCircle size={13} className="text-gray-600" />
                <span className="text-gray-600">No cookie set</span>
              </>
            )}
          </div>

          {/* Input */}
          <div className="space-y-2">
            <label className="text-[10px] text-gray-600 uppercase tracking-wide block">
              {hasCookie ? "Replace cookie" : "Cookie value"}
            </label>
            <div className="relative">
              <input
                type={showCookie ? "text" : "password"}
                value={cookie}
                onChange={(e) => setCookie(e.target.value)}
                placeholder="Paste li_at value here…"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 pr-9 text-xs outline-none focus:border-indigo-500 transition-colors placeholder-gray-600 font-mono"
              />
              <button
                type="button"
                onClick={() => setShowCookie((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-600 hover:text-gray-400 transition-colors"
                tabIndex={-1}
                aria-label={showCookie ? "Hide cookie" : "Show cookie"}
              >
                {showCookie ? <EyeOff size={13} /> : <Eye size={13} />}
              </button>
            </div>
          </div>

          {/* Save button */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => saveCookie()}
              disabled={saving || !cookie.trim()}
              className="flex items-center gap-1.5 text-xs bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-3 py-1.5 rounded-lg transition-colors"
            >
              {saving ? <Loader2 size={11} className="animate-spin" /> : <CheckCircle2 size={11} />}
              Save
            </button>
            {saved && (
              <span className="text-xs text-emerald-400 flex items-center gap-1">
                <CheckCircle2 size={11} />
                Saved successfully
              </span>
            )}
            {saveError && (
              <span className="text-xs text-red-400 flex items-center gap-1">
                <AlertCircle size={11} />
                Failed to save — try again
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
