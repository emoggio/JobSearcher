import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, ExternalLink, Zap, Star, Clock } from "lucide-react";
import { listJobs, searchJobs, createApplication, tweakCV, findRecruiters } from "../api";
import { formatDistanceToNow } from "date-fns";

const SOURCES = ["all", "linkedin", "indeed", "reed", "adzuna", "glassdoor", "totaljobs"];

function ScoreBadge({ score }: { score: number | null }) {
  if (!score) return <span className="text-xs text-gray-600">—</span>;
  const color = score >= 75 ? "text-emerald-400" : score >= 50 ? "text-yellow-400" : "text-red-400";
  return <span className={`text-sm font-semibold ${color}`}>{score}%</span>;
}

export default function Jobs() {
  const qc = useQueryClient();
  const [filters, setFilters] = useState({
    salary_min: 90000,
    date_posted: "30d",
    compatibility_min: undefined as number | undefined,
    exclude_gaming: true,
  });
  const [source, setSource] = useState("all");
  const [tweak, setTweak] = useState<{ jobId: string; text: string } | null>(null);

  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ["jobs", filters],
    queryFn: () => listJobs(filters).then((r) => r.data),
  });

  const filtered = source === "all" ? jobs : jobs.filter((j: any) => j.source === source);

  const { mutate: runSearch, isPending: searching } = useMutation({
    mutationFn: () => searchJobs(),
    onSuccess: () => setTimeout(() => qc.invalidateQueries({ queryKey: ["jobs"] }), 3000),
  });

  const { mutate: apply } = useMutation({
    mutationFn: (jobId: string) => createApplication(jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  const { mutate: getTweak, isPending: tweaking } = useMutation({
    mutationFn: (jobId: string) => tweakCV(jobId).then((r) => ({ jobId, text: r.data.tailored_cv })),
    onSuccess: (data) => setTweak(data),
  });

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Job Search</h2>
          <p className="text-sm text-gray-400">{filtered.length} roles found</p>
        </div>
        <button
          onClick={() => runSearch()}
          disabled={searching}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Search size={14} />
          {searching ? "Searching…" : "Search Now"}
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
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
          onChange={(e) =>
            setFilters((f) => ({ ...f, compatibility_min: e.target.value ? Number(e.target.value) : undefined }))
          }
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
          {SOURCES.map((s) => (
            <option key={s} value={s}>{s === "all" ? "All sources" : s}</option>
          ))}
        </select>

        <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.exclude_gaming}
            onChange={(e) => setFilters((f) => ({ ...f, exclude_gaming: e.target.checked }))}
            className="rounded"
          />
          Exclude gaming
        </label>
      </div>

      {/* Job List */}
      {isLoading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <div className="space-y-2">
          {filtered.map((job: any) => (
            <div key={job.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-gray-700 transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-medium text-white truncate">{job.title}</h3>
                    {job.remote && (
                      <span className="text-xs bg-indigo-900 text-indigo-300 px-2 py-0.5 rounded-full">Remote</span>
                    )}
                    {job.salary_estimated && (
                      <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full">~salary</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-400 mt-0.5">
                    {job.company} · {job.location}
                  </p>
                  {(job.salary_min || job.salary_max) && (
                    <p className="text-sm text-emerald-400 mt-1">
                      £{(job.salary_min / 1000).toFixed(0)}k
                      {job.salary_max && job.salary_max !== job.salary_min
                        ? ` – £${(job.salary_max / 1000).toFixed(0)}k`
                        : ""}
                    </p>
                  )}
                  <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                    <span className="capitalize">{job.source}</span>
                    {job.date_posted && (
                      <span className="flex items-center gap-1">
                        <Clock size={10} />
                        {formatDistanceToNow(new Date(job.date_posted), { addSuffix: true })}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex flex-col items-end gap-2 shrink-0">
                  <div className="flex items-center gap-1">
                    <Star size={12} className="text-gray-600" />
                    <ScoreBadge score={job.compatibility_score} />
                  </div>
                  <div className="flex gap-1.5">
                    <a
                      href={job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors"
                    >
                      <ExternalLink size={13} />
                    </a>
                    <button
                      onClick={() => getTweak(job.id)}
                      disabled={tweaking}
                      className="px-2.5 py-1 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs transition-colors"
                    >
                      Tailor CV
                    </button>
                    <button
                      onClick={() => apply(job.id)}
                      className="px-2.5 py-1 rounded-lg bg-indigo-700 hover:bg-indigo-600 text-xs transition-colors"
                    >
                      Track
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* CV Tweak Modal */}
      {tweak && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-6">
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-gray-800">
              <h3 className="font-semibold">Tailored CV</h3>
              <button onClick={() => setTweak(null)} className="text-gray-400 hover:text-white">✕</button>
            </div>
            <pre className="flex-1 overflow-auto p-4 text-sm text-gray-300 whitespace-pre-wrap font-mono">
              {tweak.text}
            </pre>
            <div className="p-4 border-t border-gray-800">
              <button
                onClick={() => navigator.clipboard.writeText(tweak.text)}
                className="text-sm bg-indigo-600 hover:bg-indigo-500 px-4 py-2 rounded-lg"
              >
                Copy to clipboard
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
