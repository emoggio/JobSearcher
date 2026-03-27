import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, ExternalLink, Star, Clock, Loader2, ChevronDown, Lightbulb, CheckCircle2 } from "lucide-react";
import { listJobs, searchJobs, createApplication, tweakCV } from "../api";
import api from "../api";
import { formatDistanceToNow } from "date-fns";

const SOURCES = ["linkedin", "indeed", "reed", "adzuna", "glassdoor", "totaljobs", "cwjobs"];

const SOURCE_COLORS: Record<string, string> = {
  linkedin: "bg-blue-900 text-blue-300",
  indeed: "bg-violet-900 text-violet-300",
  reed: "bg-red-900 text-red-300",
  adzuna: "bg-orange-900 text-orange-300",
  glassdoor: "bg-emerald-900 text-emerald-300",
  totaljobs: "bg-cyan-900 text-cyan-300",
  cwjobs: "bg-pink-900 text-pink-300",
};

const INDUSTRIES = [
  "Gaming", "Finance", "Consulting", "MedTech / HealthTech",
  "SaaS / Tech", "Energy", "Infrastructure", "Media", "Retail", "Government",
];

function ScoreBadge({ score }: { score: number | null }) {
  if (score == null) return <span className="text-xs text-gray-600">—</span>;
  const color = score >= 75 ? "bg-emerald-900 text-emerald-300" : score >= 50 ? "bg-yellow-900 text-yellow-300" : "bg-red-900 text-red-400";
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${color}`}>{score}%</span>;
}

export default function Jobs() {
  const qc = useQueryClient();
  const industryRef = useRef<HTMLDivElement>(null);

  const [filters, setFilters] = useState({ salary_min: 90000, date_posted: "30d", compatibility_min: undefined as number | undefined });
  const [excludedIndustries, setExcludedIndustries] = useState<string[]>(["Gaming"]);
  const [source, setSource] = useState("all");
  const [showIndustryDropdown, setShowIndustryDropdown] = useState(false);
  const [searchRunning, setSearchRunning] = useState(false);
  const [searchSources, setSearchSources] = useState<string[]>([]);
  const [tweak, setTweak] = useState<{ text: string } | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Close industry dropdown on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (industryRef.current && !industryRef.current.contains(e.target as Node)) {
        setShowIndustryDropdown(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Poll status while searching
  useEffect(() => {
    if (!searchRunning) return;
    const interval = setInterval(async () => {
      const { data } = await api.get("/api/jobs/status");
      if (data.running) {
        setSearchSources(SOURCES.slice(0, Math.min(SOURCES.length, searchSources.length + 1)));
      } else {
        setSearchRunning(false);
        setSearchSources([]);
        qc.invalidateQueries({ queryKey: ["jobs"] });
        clearInterval(interval);
      }
    }, 1500);
    return () => clearInterval(interval);
  }, [searchRunning, searchSources.length]);

  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ["jobs", filters],
    queryFn: () => listJobs(filters).then((r) => r.data),
  });

  const { mutate: runSearch } = useMutation({
    mutationFn: () => searchJobs(),
    onSuccess: () => { setSearchRunning(true); setSearchSources(["linkedin"]); },
  });

  const { mutate: apply, variables: applyingId } = useMutation({
    mutationFn: (jobId: string) => createApplication(jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  const { mutate: getTweak, isPending: tweaking, variables: tweakingId } = useMutation({
    mutationFn: (jobId: string) => tweakCV(jobId).then((r) => ({ text: r.data.tailored_cv })),
    onSuccess: (data) => setTweak(data),
  });

  const filtered = jobs.filter((j: any) => {
    if (source !== "all" && j.source !== source) return false;
    if (j.is_gaming && excludedIndustries.includes("Gaming")) return false;
    if (j.industry && excludedIndustries.some((ex) => j.industry?.toLowerCase().includes(ex.toLowerCase()))) return false;
    return true;
  });

  const toggleIndustry = (ind: string) => {
    setExcludedIndustries((prev) => prev.includes(ind) ? prev.filter((i) => i !== ind) : [...prev, ind]);
  };

  return (
    <div className="p-4 md:p-6 space-y-4">

      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">Jobs</h2>
          <p className="text-sm text-gray-400">{filtered.length} roles found</p>
        </div>
        <button
          onClick={() => runSearch()}
          disabled={searchRunning}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-70 px-4 py-2 rounded-lg text-sm font-medium transition-colors shrink-0"
        >
          {searchRunning ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
          {searchRunning ? "Searching…" : "Search Now"}
        </button>
      </div>

      {/* Live search progress */}
      {searchRunning && (
        <div className="bg-indigo-950/50 border border-indigo-800 rounded-xl p-3">
          <p className="text-xs text-indigo-300 mb-2 font-medium">Searching across sources…</p>
          <div className="flex flex-wrap gap-1.5">
            {SOURCES.map((s) => (
              <span
                key={s}
                className={`text-xs px-2 py-0.5 rounded-full transition-all duration-500 ${
                  searchSources.includes(s)
                    ? "bg-indigo-600 text-white"
                    : "bg-gray-800 text-gray-600"
                }`}
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-2 flex-wrap items-center">
        <select
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm"
          value={filters.date_posted}
          onChange={(e) => setFilters((f) => ({ ...f, date_posted: e.target.value }))}
        >
          <option value="24h">Last 24h</option>
          <option value="7d">Last 7 days</option>
          <option value="14d">Last 14 days</option>
          <option value="30d">Last 30 days</option>
        </select>

        <select
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm"
          value={filters.salary_min}
          onChange={(e) => setFilters((f) => ({ ...f, salary_min: Number(e.target.value) }))}
        >
          <option value={70000}>£70k+</option>
          <option value={90000}>£90k+</option>
          <option value={110000}>£110k+</option>
          <option value={130000}>£130k+</option>
        </select>

        <select
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm"
          value={filters.compatibility_min ?? ""}
          onChange={(e) => setFilters((f) => ({ ...f, compatibility_min: e.target.value ? Number(e.target.value) : undefined }))}
        >
          <option value="">Any match</option>
          <option value={50}>50%+ match</option>
          <option value={70}>70%+ match</option>
          <option value={85}>85%+ match</option>
        </select>

        <select
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm"
          value={source}
          onChange={(e) => setSource(e.target.value)}
        >
          <option value="all">All sources</option>
          {SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>

        {/* Industry multi-select */}
        <div ref={industryRef} className="relative">
          <button
            onClick={() => setShowIndustryDropdown((v) => !v)}
            className="flex items-center gap-1.5 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm"
          >
            Exclude industries
            {excludedIndustries.length > 0 && (
              <span className="bg-indigo-600 text-white text-xs px-1.5 rounded-full">{excludedIndustries.length}</span>
            )}
            <ChevronDown size={12} />
          </button>
          {showIndustryDropdown && (
            <div className="absolute top-full mt-1 left-0 bg-gray-900 border border-gray-700 rounded-xl shadow-xl z-50 py-1 min-w-48">
              {INDUSTRIES.map((ind) => (
                <button
                  key={ind}
                  onClick={() => toggleIndustry(ind)}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-gray-800 transition-colors"
                >
                  <div className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 ${excludedIndustries.includes(ind) ? "bg-indigo-600 border-indigo-600" : "border-gray-600"}`}>
                    {excludedIndustries.includes(ind) && <CheckCircle2 size={10} className="text-white" />}
                  </div>
                  {ind}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Job list */}
      {isLoading ? (
        <div className="flex items-center gap-2 text-gray-500 text-sm py-8 justify-center">
          <Loader2 size={16} className="animate-spin" /> Loading…
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-600">
          <Search size={36} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">No jobs yet — click Search Now to start</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((job: any) => (
            <div key={job.id} className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden hover:border-gray-700 transition-colors">
              {/* Main row */}
              <div
                className="p-4 cursor-pointer"
                onClick={() => setExpandedId(expandedId === job.id ? null : job.id)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-medium text-white text-sm">{job.title}</h3>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${SOURCE_COLORS[job.source] ?? "bg-gray-800 text-gray-400"}`}>
                        {job.source}
                      </span>
                      {job.remote && <span className="text-xs bg-indigo-900 text-indigo-300 px-2 py-0.5 rounded-full">Remote</span>}
                      {job.salary_estimated && <span className="text-xs bg-gray-800 text-gray-500 px-2 py-0.5 rounded-full">~salary</span>}
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">{job.company} · {job.location}</p>
                    {(job.salary_min || job.salary_max) && (
                      <p className="text-xs text-emerald-400 mt-0.5">
                        £{(job.salary_min / 1000).toFixed(0)}k{job.salary_max && job.salary_max !== job.salary_min ? ` – £${(job.salary_max / 1000).toFixed(0)}k` : ""}
                      </p>
                    )}
                    {job.date_posted && (
                      <p className="text-xs text-gray-600 mt-0.5 flex items-center gap-1">
                        <Clock size={10} />
                        {formatDistanceToNow(new Date(job.date_posted), { addSuffix: true })}
                      </p>
                    )}
                  </div>

                  {/* Score */}
                  <div className="flex flex-col items-end gap-1.5 shrink-0">
                    <div className="flex items-center gap-1">
                      <Star size={11} className="text-gray-600" />
                      <ScoreBadge score={job.compatibility_score} />
                    </div>
                  </div>
                </div>

                {/* Score reason — always visible if available */}
                {job.score_reason && (
                  <p className="text-xs text-gray-500 mt-2 italic">{job.score_reason}</p>
                )}
              </div>

              {/* Expanded actions + suggestion */}
              {expandedId === job.id && (
                <div className="border-t border-gray-800 px-4 py-3 space-y-3 bg-gray-950/50">
                  {/* Tailoring suggestion */}
                  {job.score_suggestion && (
                    <div className="flex gap-2 bg-amber-950/30 border border-amber-900/50 rounded-lg p-2.5">
                      <Lightbulb size={13} className="text-amber-400 shrink-0 mt-0.5" />
                      <p className="text-xs text-amber-200">{job.score_suggestion}</p>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2 flex-wrap">
                    <a
                      href={job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs transition-colors"
                    >
                      <ExternalLink size={12} /> View job
                    </a>
                    <button
                      onClick={() => getTweak(job.id)}
                      disabled={tweaking && tweakingId === job.id}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs transition-colors disabled:opacity-50"
                    >
                      {tweaking && tweakingId === job.id ? <Loader2 size={12} className="animate-spin" /> : null}
                      Tailor CV
                    </button>
                    <button
                      onClick={() => apply(job.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-700 hover:bg-indigo-600 text-xs transition-colors"
                    >
                      Track application
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* CV Tweak Modal */}
      {tweak && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-gray-800">
              <h3 className="font-semibold text-sm">Tailored CV</h3>
              <button onClick={() => setTweak(null)} className="text-gray-400 hover:text-white text-lg leading-none">✕</button>
            </div>
            <pre className="flex-1 overflow-auto p-4 text-xs text-gray-300 whitespace-pre-wrap font-mono leading-relaxed">
              {tweak.text}
            </pre>
            <div className="p-4 border-t border-gray-800 flex gap-2">
              <button
                onClick={() => navigator.clipboard.writeText(tweak.text)}
                className="text-sm bg-indigo-600 hover:bg-indigo-500 px-4 py-2 rounded-lg"
              >
                Copy to clipboard
              </button>
              <button onClick={() => setTweak(null)} className="text-sm bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
