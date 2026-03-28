import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listApplications, updateApplication, deleteApplication } from "../api";
import {
  Trash2, ExternalLink, ChevronDown, ChevronUp, Calendar, FileText,
} from "lucide-react";
import { format, parseISO } from "date-fns";

const STATUSES = ["applied", "screen", "interview", "offer", "rejected"];

const STATUS_COLORS: Record<string, string> = {
  applied: "bg-blue-900 text-blue-300",
  screen: "bg-yellow-900 text-yellow-300",
  interview: "bg-purple-900 text-purple-300",
  offer: "bg-emerald-900 text-emerald-300",
  rejected: "bg-red-900 text-red-400",
};

function AppCard({ app }: { app: any }) {
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [notes, setNotes] = useState(app.notes || "");
  const [actionDate, setActionDate] = useState(
    app.next_action_date ? app.next_action_date.slice(0, 10) : ""
  );
  const [nextAction, setNextAction] = useState(app.next_action || "");
  const [saving, setSaving] = useState(false);

  const { mutate: updateStatus } = useMutation({
    mutationFn: (status: string) => updateApplication(app.id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  const { mutate: remove } = useMutation({
    mutationFn: () => deleteApplication(app.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  async function saveDetails() {
    setSaving(true);
    try {
      await updateApplication(app.id, {
        notes: notes || null,
        next_action: nextAction || null,
        next_action_date: actionDate ? new Date(actionDate).toISOString() : null,
      });
      qc.invalidateQueries({ queryKey: ["applications"] });
    } finally {
      setSaving(false);
    }
  }

  const score = app.job_score;
  const scoreTier = score >= 70 ? "text-emerald-400" : score >= 50 ? "text-yellow-400" : "text-red-400";

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      {/* Card header */}
      <div
        className="p-3 cursor-pointer hover:bg-gray-800/40 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-sm font-medium text-white truncate">{app.job_title}</p>
            <p className="text-xs text-gray-500 truncate">{app.job_company}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {score != null && (
              <span className={`text-xs font-bold ${scoreTier}`}>{Math.round(score)}%</span>
            )}
            {expanded ? <ChevronUp size={13} className="text-gray-600" /> : <ChevronDown size={13} className="text-gray-600" />}
          </div>
        </div>

        {app.applied_at && (
          <p className="text-[10px] text-gray-700 mt-1">
            Applied {format(parseISO(app.applied_at), "d MMM yyyy")}
          </p>
        )}

        {app.notes && !expanded && (
          <p className="text-[11px] text-gray-600 mt-1 truncate italic">{app.notes}</p>
        )}
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="border-t border-gray-800 p-3 space-y-3">
          {/* Status buttons */}
          <div>
            <p className="text-[10px] text-gray-600 font-medium uppercase mb-1.5">Move to</p>
            <div className="flex gap-1 flex-wrap">
              {STATUSES.filter((s) => s !== app.status).map((s) => (
                <button
                  key={s}
                  onClick={() => updateStatus(s)}
                  className={`text-[10px] px-2 py-1 rounded-full capitalize transition-colors border ${
                    STATUS_COLORS[s]
                  } border-current opacity-70 hover:opacity-100`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Next action */}
          <div>
            <label className="text-[10px] text-gray-600 font-medium uppercase block mb-1">
              <Calendar size={9} className="inline mr-1" />Next action
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={nextAction}
                onChange={(e) => setNextAction(e.target.value)}
                placeholder="e.g. Follow up with recruiter"
                className="flex-1 bg-gray-950 border border-gray-700 rounded px-2 py-1 text-xs outline-none focus:border-indigo-500"
              />
              <input
                type="date"
                value={actionDate}
                onChange={(e) => setActionDate(e.target.value)}
                className="bg-gray-950 border border-gray-700 rounded px-2 py-1 text-xs outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="text-[10px] text-gray-600 font-medium uppercase block mb-1">
              <FileText size={9} className="inline mr-1" />Notes
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Anything to remember about this application…"
              className="w-full bg-gray-950 border border-gray-700 rounded px-2 py-1.5 text-xs outline-none focus:border-indigo-500 resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between pt-1">
            <div className="flex gap-2">
              <button
                onClick={saveDetails}
                disabled={saving}
                className="text-xs bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save"}
              </button>
              {app.job_url && (
                <a
                  href={app.job_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs flex items-center gap-1 text-gray-400 hover:text-white bg-gray-800 px-3 py-1.5 rounded-lg"
                >
                  <ExternalLink size={11} /> View job
                </a>
              )}
            </div>
            <button
              onClick={() => remove()}
              className="text-gray-700 hover:text-red-400 transition-colors"
            >
              <Trash2 size={13} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Applications() {
  const { data: apps = [], isLoading } = useQuery({
    queryKey: ["applications"],
    queryFn: () => listApplications().then((r) => r.data),
  });

  const grouped = STATUSES.reduce((acc, s) => {
    acc[s] = (apps as any[]).filter((a) => a.status === s);
    return acc;
  }, {} as Record<string, any[]>);

  const total = (apps as any[]).length;

  return (
    <div className="p-4 md:p-6">
      <div className="mb-6">
        <h2 className="text-xl font-semibold">Applications</h2>
        <p className="text-sm text-gray-500 mt-0.5">{total} tracked</p>
      </div>

      {isLoading ? (
        <p className="text-gray-600 text-sm">Loading…</p>
      ) : total === 0 ? (
        <p className="text-gray-600 text-sm">No applications yet — track a job from the Jobs page.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
          {STATUSES.map((status) => (
            <div key={status} className="space-y-2">
              <div className="flex items-center justify-between mb-2">
                <span className={`text-xs font-medium px-2 py-1 rounded-full capitalize ${STATUS_COLORS[status]}`}>
                  {status}
                </span>
                <span className="text-xs text-gray-600">{grouped[status].length}</span>
              </div>
              {grouped[status].map((app: any) => (
                <AppCard key={app.id} app={app} />
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
