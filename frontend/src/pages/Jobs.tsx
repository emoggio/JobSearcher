import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Search, ExternalLink, Star, Clock, Loader2, ChevronDown,
  Lightbulb, CheckCircle2, Link, ScrollText, Users, Building2,
  MapPin, Banknote, Calendar, ChevronRight, X, Briefcase,
} from "lucide-react";
import { listJobs, searchJobs, createApplication, tweakCV, importJobUrl, getLogs } from "../api";
import api from "../api";
import { formatDistanceToNow, format, parseISO } from "date-fns";

const SOURCES = ["linkedin", "indeed", "reed", "adzuna", "glassdoor", "totaljobs", "cwjobs", "wellfound", "google"];

const SOURCE_COLORS: Record<string, string> = {
  linkedin: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  indeed: "bg-violet-500/15 text-violet-400 border-violet-500/30",
  reed: "bg-red-500/15 text-red-400 border-red-500/30",
  adzuna: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  glassdoor: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  totaljobs: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
  cwjobs: "bg-pink-500/15 text-pink-400 border-pink-500/30",
  wellfound: "bg-teal-500/15 text-teal-400 border-teal-500/30",
  google: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
};

const INDUSTRIES = [
  "Gaming", "Finance", "Consulting", "MedTech / HealthTech",
  "SaaS / Tech", "Energy", "Infrastructure", "Media", "Retail", "Government",
];

function ScoreBadge({ score }: { score: number | null }) {
  if (score == null) return null;
  const tier = score >= 75 ? "high" : score >= 50 ? "mid" : "low";
  const styles = {
    high: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
    mid: "bg-yellow-500/20 text-yellow-300 border-yellow-500/40",
    low: "bg-red-500/20 text-red-400 border-red-500/40",
  }[tier];
  return (
    <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${styles}`}>
      {score}%
    </span>
  );
}

function ScoreBar({ score }: { score: number | null }) {
  if (score == null) return null;
  const color = score >= 75 ? "bg-emerald-500" : score >= 50 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="w-full bg-gray-800 rounded-full h-1 mt-1.5">
      <div className={`${color} h-1 rounded-full transition-all`} style={{ width: `${score}%` }} />
    </div>
  );
}

function formatSalary(min?: number, max?: number) {
  if (!min && !max) return null;
  const fmt = (n: number) => n >= 1000 ? `£${(n / 1000).toFixed(0)}k` : `£${n}`;
  if (min && max && max !== min) return `${fmt(min)} – ${fmt(max)}`;
  if (min) return `${fmt(min)}+`;
  if (max) return `up to ${fmt(max)}`;
  return null;
}

function formatDate(datePosted?: string | null, dateScraped?: string | null) {
  const d = datePosted || dateScraped;
  if (!d) return null;
  try {
    const dt = parseISO(d);
    const distance = formatDistanceToNow(dt, { addSuffix: true });
    return { distance, full: format(dt, "d MMM yyyy") };
  } catch {
    return null;
  }
}

function JobCard({
  job, onApply, onTweak, tweaking, applying, highlighted,
}: {
  job: any;
  onApply: (id: string) => void;
  onTweak: (id: string) => void;
  tweaking: boolean;
  applying: boolean;
  highlighted?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const salary = formatSalary(job.salary_min, job.salary_max);
  const date = formatDate(job.date_posted, job.date_scraped);
  const isRecruiter = job.source === "reed" || job.source === "cwjobs" || job.source === "totaljobs";

  const recruiterSearchUrl = `https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(
    `recruiter ${job.company} hiring ${job.title}`
  )}&origin=GLOBAL_SEARCH_HEADER`;

  return (
    <div className={`bg-gray-900 border rounded-xl overflow-hidden transition-all ${
      highlighted ? "border-emerald-600/60 shadow-lg shadow-emerald-950/30 ring-1 ring-emerald-600/20" :
      expanded ? "border-indigo-700/50 shadow-lg shadow-indigo-950/30" : "border-gray-800 hover:border-gray-700"
    }`}>
      {highlighted && (
        <div className="bg-emerald-900/30 border-b border-emerald-800/40 px-4 py-1.5 flex items-center gap-1.5">
          <CheckCircle2 size={11} className="text-emerald-400" />
          <span className="text-[11px] text-emerald-400 font-medium">Imported just now</span>
        </div>
      )}
      {/* Main card row */}
      <div className="p-4 cursor-pointer" onClick={() => setExpanded((v) => !v)}>
        <div className="flex gap-3">
          {/* Score bar on left */}
          <div className="flex flex-col items-center gap-1 shrink-0 pt-0.5">
            <ScoreBadge score={job.compatibility_score} />
            {job.compatibility_score != null && (
              <div className="w-8 bg-gray-800 rounded-full h-0.5">
                <div
                  className={`h-0.5 rounded-full ${job.compatibility_score >= 75 ? "bg-emerald-500" : job.compatibility_score >= 50 ? "bg-yellow-500" : "bg-red-500"}`}
                  style={{ width: `${job.compatibility_score}%` }}
                />
              </div>
            )}
          </div>

          {/* Main content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="font-semibold text-white text-sm leading-tight">{job.title}</h3>
                  {job.remote && (
                    <span className="text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-1.5 py-0.5 rounded-full">
                      Remote
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1 mt-0.5 flex-wrap">
                  <Building2 size={11} className="text-gray-500 shrink-0" />
                  <span className="text-xs text-gray-400">{job.company}</span>
                  {job.location && (
                    <>
                      <span className="text-gray-700">·</span>
                      <MapPin size={11} className="text-gray-500 shrink-0" />
                      <span className="text-xs text-gray-500">{job.location}</span>
                    </>
                  )}
                </div>
              </div>
              <ChevronRight
                size={14}
                className={`text-gray-600 shrink-0 transition-transform mt-0.5 ${expanded ? "rotate-90" : ""}`}
              />
            </div>

            {/* Metadata row */}
            <div className="flex items-center gap-3 mt-2 flex-wrap">
              {salary && (
                <span className="flex items-center gap-1 text-xs text-emerald-400">
                  <Banknote size={11} />
                  {salary}
                  {job.salary_estimated && <span className="text-gray-600 text-[10px]">est.</span>}
                </span>
              )}
              {date && (
                <span className="flex items-center gap-1 text-xs text-gray-600" title={date.full}>
                  <Clock size={11} />
                  {date.distance}
                </span>
              )}
              <span className={`text-[10px] px-1.5 py-0.5 rounded border ${SOURCE_COLORS[job.source] ?? "bg-gray-800 text-gray-400 border-gray-700"}`}>
                {job.source}
              </span>
              {isRecruiter && (
                <span className="flex items-center gap-1 text-[10px] text-purple-400 bg-purple-500/10 border border-purple-500/20 px-1.5 py-0.5 rounded">
                  <Users size={9} />
                  Agency
                </span>
              )}
            </div>

            {/* Score reason — teaser */}
            {job.score_reason && !expanded && (
              <p className="text-[11px] text-gray-600 mt-1.5 truncate italic">{job.score_reason}</p>
            )}
          </div>
        </div>
      </div>

      {/* Expanded detail panel */}
      {expanded && (
        <div className="border-t border-gray-800 bg-gray-950/60">
          {/* Score reason + gap analysis */}
          {(job.score_reason || job.score_suggestion) && (
            <div className="px-4 pt-3 pb-0 space-y-2">
              {job.score_reason && (
                <div className="flex gap-2 items-start">
                  <Star size={12} className="text-indigo-400 shrink-0 mt-0.5" />
                  <p className="text-xs text-gray-400 italic">{job.score_reason}</p>
                </div>
              )}
              {job.score_suggestion && (
                <div className="flex gap-2 items-start bg-amber-950/30 border border-amber-900/40 rounded-lg p-2.5">
                  <Lightbulb size={12} className="text-amber-400 shrink-0 mt-0.5" />
                  <p className="text-xs text-amber-200">{job.score_suggestion}</p>
                </div>
              )}
            </div>
          )}

          {/* Job description preview */}
          {job.description && (
            <div className="px-4 pt-3 pb-0">
              <p className="text-[10px] text-gray-600 font-medium uppercase tracking-wide mb-1.5">Description</p>
              <p className="text-xs text-gray-500 leading-relaxed line-clamp-5">
                {job.description.slice(0, 600)}{job.description.length > 600 ? "…" : ""}
              </p>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-2 flex-wrap p-4">
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-medium transition-colors"
              onClick={(e) => e.stopPropagation()}
            >
              <ExternalLink size={12} /> Apply
            </a>

            <a
              href={recruiterSearchUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-700/40 hover:bg-purple-700/60 text-purple-300 text-xs transition-colors border border-purple-600/30"
              onClick={(e) => e.stopPropagation()}
              title="Find recruiter or hiring manager on LinkedIn"
            >
              <Users size={12} /> Find Recruiter
            </a>

            <button
              onClick={(e) => { e.stopPropagation(); onTweak(job.id); }}
              disabled={tweaking}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs transition-colors disabled:opacity-50"
            >
              {tweaking ? <Loader2 size={12} className="animate-spin" /> : <Briefcase size={12} />}
              Tailor CV
            </button>

            <button
              onClick={(e) => { e.stopPropagation(); onApply(job.id); }}
              disabled={applying}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs transition-colors"
            >
              <CheckCircle2 size={12} /> Track
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Jobs() {
  const qc = useQueryClient();
  const industryRef = useRef<HTMLDivElement>(null);

  const [filters, setFilters] = useState({
    salary_min: 90000,
    date_posted: "30d",
    compatibility_min: undefined as number | undefined,
  });
  const [excludedIndustries, setExcludedIndustries] = useState<string[]>(["Gaming"]);
  const [source, setSource] = useState("all");
  const [showIndustryDropdown, setShowIndustryDropdown] = useState(false);
  const [searchRunning, setSearchRunning] = useState(false);
  const [searchSources, setSearchSources] = useState<string[]>([]);
  const [tweak, setTweak] = useState<{ text: string; jobTitle: string } | null>(null);
  const [importUrl, setImportUrl] = useState("");
  const [showLogs, setShowLogs] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [logTab, setLogTab] = useState<"logs" | "debug">("logs");
  const [applyingId, setApplyingId] = useState<string | null>(null);
  const [tweakingId, setTweakingId] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<"score" | "date">("score");
  const [importStatus, setImportStatus] = useState<{ ok: boolean; msg: string } | null>(null);
  const [lastImportedId, setLastImportedId] = useState<string | null>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (industryRef.current && !industryRef.current.contains(e.target as Node)) {
        setShowIndustryDropdown(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    api.get("/api/jobs/status").then(({ data }) => {
      if (data.running) { setSearchRunning(true); setSearchSources(["linkedin"]); }
    }).catch(() => {});
  }, []);

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

  const { data: searchStatus } = useQuery({
    queryKey: ["search-status"],
    queryFn: () => api.get("/api/jobs/status").then((r) => r.data),
    refetchInterval: searchRunning ? 3000 : false,
  });

  const { mutate: runSearch } = useMutation({
    mutationFn: () => searchJobs(),
    onSuccess: () => { setSearchRunning(true); setSearchSources(["linkedin"]); },
  });

  const { mutate: importMutate, isPending: importing } = useMutation({
    mutationFn: (url: string) => importJobUrl(url),
    onSuccess: (data) => {
      setImportUrl("");
      setImportStatus({ ok: true, msg: `Imported: ${data.data?.title || "job"} @ ${data.data?.company || ""}` });
      setLastImportedId(data.data?.id ?? null);
      qc.invalidateQueries({ queryKey: ["jobs"] });
      setTimeout(() => setImportStatus(null), 5000);
    },
    onError: () => {
      setImportStatus({ ok: false, msg: "Could not import — try a different URL or paste the job text." });
      setTimeout(() => setImportStatus(null), 6000);
    },
  });

  async function openLogs() {
    const { data } = await getLogs(200);
    setLogs(data.lines);
    setShowLogs(true);
  }

  async function handleApply(jobId: string) {
    setApplyingId(jobId);
    try {
      await createApplication(jobId);
      qc.invalidateQueries({ queryKey: ["applications"] });
    } finally {
      setApplyingId(null);
    }
  }

  async function handleTweak(jobId: string, jobTitle: string) {
    setTweakingId(jobId);
    try {
      const { data } = await tweakCV(jobId);
      setTweak({ text: data.tailored_cv, jobTitle });
    } finally {
      setTweakingId(null);
    }
  }

  const filtered = jobs
    .filter((j: any) => {
      if (source !== "all" && j.source !== source) return false;
      if (j.is_gaming && excludedIndustries.includes("Gaming")) return false;
      if (j.industry && excludedIndustries.some((ex) => j.industry?.toLowerCase().includes(ex.toLowerCase()))) return false;
      return true;
    })
    .sort((a: any, b: any) => {
      if (sortBy === "score") {
        return (b.compatibility_score ?? 0) - (a.compatibility_score ?? 0);
      }
      // Sort by date_posted desc, then date_scraped desc
      const da = a.date_posted || a.date_scraped || "";
      const db_ = b.date_posted || b.date_scraped || "";
      return db_.localeCompare(da);
    });

  const toggleIndustry = (ind: string) =>
    setExcludedIndustries((prev) => prev.includes(ind) ? prev.filter((i) => i !== ind) : [...prev, ind]);

  const highMatch = filtered.filter((j: any) => (j.compatibility_score ?? 0) >= 70).length;

  return (
    <div className="p-4 md:p-6 max-w-3xl mx-auto space-y-4">

      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">Job Matches</h2>
          <p className="text-sm text-gray-500">
            {filtered.length} roles
            {highMatch > 0 && <span className="text-emerald-400 ml-1">· {highMatch} strong matches</span>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={openLogs}
            className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            title="View logs"
          >
            <ScrollText size={14} />
          </button>
          <button
            onClick={() => runSearch()}
            disabled={searchRunning}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 px-4 py-2 rounded-lg text-sm font-medium transition-colors shrink-0"
          >
            {searchRunning ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
            {searchRunning ? "Searching…" : "Search"}
          </button>
        </div>
      </div>

      {/* URL import */}
      <form
        onSubmit={(e) => { e.preventDefault(); if (importUrl.trim()) importMutate(importUrl.trim()); }}
        className="flex gap-2"
      >
        <div className="flex-1 flex items-center gap-2 bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 focus-within:border-indigo-500 transition-colors">
          <Link size={13} className="text-gray-600 shrink-0" />
          <input
            type="text"
            value={importUrl}
            onChange={(e) => setImportUrl(e.target.value)}
            placeholder="Paste any job URL to import…"
            className="flex-1 bg-transparent text-sm outline-none placeholder-gray-700"
          />
        </div>
        <button
          type="submit"
          disabled={importing || !importUrl.trim()}
          className="px-3 py-2 bg-gray-800 hover:bg-gray-700 disabled:opacity-40 rounded-lg text-sm transition-colors shrink-0"
        >
          {importing ? <Loader2 size={14} className="animate-spin" /> : "Import"}
        </button>
      </form>

      {/* Import status banner */}
      {importStatus && (
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs ${
          importStatus.ok
            ? "bg-emerald-900/40 border border-emerald-700/50 text-emerald-300"
            : "bg-red-900/40 border border-red-700/50 text-red-300"
        }`}>
          {importStatus.ok ? <CheckCircle2 size={13} /> : <X size={13} />}
          {importStatus.msg}
        </div>
      )}

      {/* Live search progress */}
      {searchRunning && (
        <div className="bg-indigo-950/40 border border-indigo-800/50 rounded-xl p-3">
          <div className="flex items-center gap-2 mb-2">
            <Loader2 size={12} className="animate-spin text-indigo-400" />
            <p className="text-xs text-indigo-300 font-medium">Scanning job boards…</p>
          </div>
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
          className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-1.5 text-xs"
          value={filters.date_posted}
          onChange={(e) => setFilters((f) => ({ ...f, date_posted: e.target.value }))}
        >
          <option value="24h">Last 24h</option>
          <option value="7d">Last 7d</option>
          <option value="14d">Last 14d</option>
          <option value="30d">Last 30d</option>
        </select>

        <select
          className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-1.5 text-xs"
          value={filters.salary_min}
          onChange={(e) => setFilters((f) => ({ ...f, salary_min: Number(e.target.value) }))}
        >
          <option value={70000}>£70k+</option>
          <option value={90000}>£90k+</option>
          <option value={110000}>£110k+</option>
          <option value={130000}>£130k+</option>
        </select>

        <select
          className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-1.5 text-xs"
          value={filters.compatibility_min ?? ""}
          onChange={(e) => setFilters((f) => ({ ...f, compatibility_min: e.target.value ? Number(e.target.value) : undefined }))}
        >
          <option value="">Any match</option>
          <option value={50}>50%+ match</option>
          <option value={70}>70%+ match</option>
          <option value={85}>85%+ match</option>
        </select>

        <select
          className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-1.5 text-xs"
          value={source}
          onChange={(e) => setSource(e.target.value)}
        >
          <option value="all">All sources</option>
          {SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>

        <select
          className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-1.5 text-xs"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as "score" | "date")}
        >
          <option value="score">Sort: Best match</option>
          <option value="date">Sort: Newest first</option>
        </select>

        {/* Industry multi-select */}
        <div ref={industryRef} className="relative">
          <button
            onClick={() => setShowIndustryDropdown((v) => !v)}
            className="flex items-center gap-1.5 bg-gray-900 border border-gray-800 rounded-lg px-3 py-1.5 text-xs"
          >
            Exclude
            {excludedIndustries.length > 0 && (
              <span className="bg-indigo-600 text-white text-[10px] px-1.5 rounded-full">{excludedIndustries.length}</span>
            )}
            <ChevronDown size={11} />
          </button>
          {showIndustryDropdown && (
            <div className="absolute top-full mt-1 left-0 bg-gray-900 border border-gray-800 rounded-xl shadow-2xl z-50 py-1 min-w-48">
              {INDUSTRIES.map((ind) => (
                <button
                  key={ind}
                  onClick={() => toggleIndustry(ind)}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-gray-800 transition-colors"
                >
                  <div className={`w-3.5 h-3.5 rounded border flex items-center justify-center shrink-0 ${excludedIndustries.includes(ind) ? "bg-indigo-600 border-indigo-600" : "border-gray-600"}`}>
                    {excludedIndustries.includes(ind) && <CheckCircle2 size={9} className="text-white" />}
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
        <div className="flex items-center gap-2 text-gray-500 text-sm py-12 justify-center">
          <Loader2 size={16} className="animate-spin" /> Loading…
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-600">
          <Search size={40} className="mx-auto mb-3 opacity-20" />
          <p className="text-sm font-medium mb-1">No jobs yet</p>
          <p className="text-xs">Click Search to scan all job boards</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((job: any) => (
            <JobCard
              key={job.id}
              job={job}
              onApply={handleApply}
              onTweak={(id) => handleTweak(id, job.title)}
              tweaking={tweakingId === job.id}
              applying={applyingId === job.id}
              highlighted={job.id === lastImportedId}
            />
          ))}
        </div>
      )}

      {/* Log drawer */}
      {showLogs && (
        <div className="fixed inset-0 bg-black/80 flex items-end justify-center z-50 p-4" onClick={() => setShowLogs(false)}>
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-3xl max-h-[70vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setLogTab("logs")}
                  className={`text-sm font-medium flex items-center gap-1.5 px-2 py-1 rounded transition-colors ${logTab === "logs" ? "text-white bg-gray-800" : "text-gray-500 hover:text-gray-300"}`}
                >
                  <ScrollText size={12} /> Logs
                </button>
                <button
                  onClick={() => setLogTab("debug")}
                  className={`text-sm font-medium flex items-center gap-1.5 px-2 py-1 rounded transition-colors ${logTab === "debug" ? "text-white bg-gray-800" : "text-gray-500 hover:text-gray-300"}`}
                >
                  Source Health
                  {searchStatus?.by_source && Object.values(searchStatus.by_source).some((v: any) => v === 0) && (
                    <span className="bg-red-500/20 text-red-400 text-[10px] px-1.5 rounded-full border border-red-500/30">!</span>
                  )}
                </button>
              </div>
              <button onClick={() => setShowLogs(false)} className="text-gray-500 hover:text-white">
                <X size={16} />
              </button>
            </div>

            {logTab === "logs" ? (
              <div className="flex-1 overflow-auto p-4 font-mono text-[11px] text-gray-500 space-y-0.5">
                {logs.length === 0 ? (
                  <p className="text-gray-700">No logs yet.</p>
                ) : (
                  logs.map((line, i) => (
                    <p key={i} className={
                      line.includes("[ERROR]") ? "text-red-400" :
                      line.includes("[WARNING]") ? "text-yellow-600" :
                      line.includes("Saved") || line.includes("complete") ? "text-emerald-500" :
                      ""
                    }>
                      {line}
                    </p>
                  ))
                )}
              </div>
            ) : (
              <div className="flex-1 overflow-auto p-4 space-y-4">
                {/* Last search stats */}
                {searchStatus?.last_run && (
                  <div>
                    <p className="text-xs text-gray-500 mb-2">
                      Last search: <span className="text-gray-300">{new Date(searchStatus.last_run).toLocaleString()}</span>
                      {" · "}<span className="text-emerald-400">{searchStatus.last_count} new jobs</span>
                    </p>
                  </div>
                )}

                {/* Per-source counts */}
                {searchStatus?.by_source && Object.keys(searchStatus.by_source).length > 0 ? (
                  <div>
                    <p className="text-xs text-gray-600 font-medium uppercase tracking-wide mb-3">Jobs scraped per source (last search)</p>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {SOURCES.map((src) => {
                        const count = searchStatus.by_source[src] ?? null;
                        const hasError = searchStatus.source_errors?.[src]?.length > 0;
                        const color = hasError ? "border-red-800/50 bg-red-950/20" :
                          count === null ? "border-gray-800 bg-gray-900/40" :
                          count === 0 ? "border-yellow-800/50 bg-yellow-950/20" :
                          "border-emerald-800/40 bg-emerald-950/15";
                        const textColor = hasError ? "text-red-400" :
                          count === null ? "text-gray-600" :
                          count === 0 ? "text-yellow-500" :
                          "text-emerald-400";
                        return (
                          <div key={src} className={`border rounded-lg p-3 ${color}`}>
                            <p className="text-xs text-gray-400 capitalize">{src}</p>
                            <p className={`text-lg font-bold ${textColor}`}>
                              {count === null ? "—" : count}
                            </p>
                            {hasError && (
                              <p className="text-[10px] text-red-400 mt-0.5 truncate">
                                {searchStatus.source_errors[src][0]}
                              </p>
                            )}
                            {count === 0 && !hasError && (
                              <p className="text-[10px] text-yellow-600 mt-0.5">0 results — may be blocked</p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-gray-600">Run a search to see per-source stats here.</p>
                )}

                {/* Errors */}
                {searchStatus?.errors?.length > 0 && (
                  <div>
                    <p className="text-xs text-gray-600 font-medium uppercase tracking-wide mb-2">Search errors</p>
                    {searchStatus.errors.map((e: string, i: number) => (
                      <p key={i} className="text-xs text-red-400 font-mono">{e}</p>
                    ))}
                  </div>
                )}

                {/* Tips for zero-result sources */}
                {searchStatus?.by_source && Object.entries(searchStatus.by_source).some(([, v]) => v === 0) && (
                  <div className="bg-amber-950/20 border border-amber-800/30 rounded-lg p-3 space-y-1.5">
                    <p className="text-xs text-amber-400 font-medium">Why some sources return 0 results</p>
                    <ul className="text-[11px] text-amber-200/70 space-y-1 list-disc list-inside">
                      <li>LinkedIn, Indeed, Glassdoor use anti-bot detection — try running from a residential IP</li>
                      <li>Sources may have temporarily changed their HTML — selector updates may be needed</li>
                      <li>Running multiple searches quickly can trigger rate limiting</li>
                      <li>Reed and Adzuna use APIs and are most reliable</li>
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* CV Tweak Modal */}
      {tweak && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-gray-800">
              <div>
                <h3 className="font-semibold text-sm">Tailored CV</h3>
                <p className="text-xs text-gray-500">{tweak.jobTitle}</p>
              </div>
              <button onClick={() => setTweak(null)} className="text-gray-500 hover:text-white">
                <X size={16} />
              </button>
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
