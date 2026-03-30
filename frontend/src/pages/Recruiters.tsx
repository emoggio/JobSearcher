import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listRecruiters, updateApplication } from "../api";
import api from "../api";
import { ExternalLink, Copy, Users, Briefcase, UserCheck, Check } from "lucide-react";
import { useState } from "react";

const LABEL_STYLES: Record<string, string> = {
  "Internal Recruiter": "bg-blue-500/15 text-blue-400 border-blue-500/30",
  "Hiring Manager":     "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  "Team / Peer":        "bg-purple-500/15 text-purple-400 border-purple-500/30",
};

const LABEL_ICONS: Record<string, React.ReactNode> = {
  "Internal Recruiter": <Users size={11} />,
  "Hiring Manager":     <UserCheck size={11} />,
  "Team / Peer":        <Briefcase size={11} />,
};

const CONTACTED_STYLES: Record<string, string> = {
  no:      "bg-gray-800 text-gray-500 hover:bg-gray-700",
  sent:    "bg-yellow-900/40 text-yellow-400 border border-yellow-700/40",
  replied: "bg-emerald-900/40 text-emerald-400 border border-emerald-700/40",
};

export default function Recruiters() {
  const qc = useQueryClient();
  const [copied, setCopied] = useState<string | null>(null);

  const { data: recruiters = [] } = useQuery({
    queryKey: ["recruiters"],
    queryFn: () => listRecruiters().then((r) => r.data),
  });

  async function setContacted(id: string, status: string) {
    await api.patch(`/api/recruiters/${id}`, { contacted: status });
    qc.invalidateQueries({ queryKey: ["recruiters"] });
  }

  function copyMsg(id: string, text: string) {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  }

  // Group by job
  const byJob: Record<string, any[]> = {};
  for (const r of recruiters as any[]) {
    const key = `${r.job_id ?? "misc"}__${r.company}`;
    if (!byJob[key]) byJob[key] = [];
    byJob[key].push(r);
  }

  return (
    <div className="p-4 md:p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Recruiter Leads</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Each search opens LinkedIn pre-filtered to the right people. Copy the message before connecting.
        </p>
      </div>

      {recruiters.length === 0 ? (
        <p className="text-gray-600 text-sm py-12 text-center">
          No leads yet — click "Find Recruiter" on any job card.
        </p>
      ) : (
        <div className="space-y-5">
          {Object.entries(byJob).map(([key, recs]) => {
            const first = recs[0];
            return (
              <div key={key} className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                {/* Job header */}
                <div className="px-4 py-3 border-b border-gray-800 bg-gray-900/80">
                  <p className="font-medium text-white text-sm">{first.company}</p>
                  {first.title && <p className="text-xs text-gray-500 mt-0.5">{first.title}</p>}
                </div>

                {/* Search targets */}
                <div className="divide-y divide-gray-800/60">
                  {recs.map((rec: any) => {
                    const labelStyle = LABEL_STYLES[rec.name] ?? "bg-gray-800 text-gray-400 border-gray-700";
                    const labelIcon = LABEL_ICONS[rec.name] ?? <Users size={11} />;
                    return (
                      <div key={rec.id} className="p-4 space-y-3">
                        <div className="flex items-center justify-between gap-3 flex-wrap">
                          <div className="flex items-center gap-2">
                            <span className={`flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full border font-medium ${labelStyle}`}>
                              {labelIcon}
                              {rec.name}
                            </span>
                            <span className="text-xs text-gray-500">{rec.title}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            {/* Contacted status */}
                            <select
                              value={rec.contacted ?? "no"}
                              onChange={(e) => setContacted(rec.id, e.target.value)}
                              className={`text-xs px-2 py-1 rounded-lg border-0 outline-none cursor-pointer ${CONTACTED_STYLES[rec.contacted ?? "no"]}`}
                            >
                              <option value="no">Not contacted</option>
                              <option value="sent">Message sent</option>
                              <option value="replied">Replied</option>
                            </select>
                            <a
                              href={rec.linkedin_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-700/80 hover:bg-blue-600 text-xs font-medium transition-colors shrink-0"
                            >
                              <ExternalLink size={12} /> Search
                            </a>
                          </div>
                        </div>

                        {rec.message_draft && (
                          <div className="bg-gray-800/70 rounded-lg p-3 flex gap-3 items-start">
                            <p className="flex-1 text-xs text-gray-300 leading-relaxed">{rec.message_draft}</p>
                            <button
                              onClick={() => copyMsg(rec.id, rec.message_draft)}
                              className="shrink-0 p-1.5 rounded-lg hover:bg-gray-700 text-gray-500 hover:text-white transition-colors"
                              title="Copy message"
                            >
                              {copied === rec.id ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
