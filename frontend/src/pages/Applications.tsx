import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listApplications, updateApplication, deleteApplication } from "../api";
import {
  ExternalLink, Trash2, ChevronDown, ChevronUp,
  Loader2, GripVertical, LayoutDashboard, ArrowRightLeft,
} from "lucide-react";
import { format, parseISO } from "date-fns";

const COLUMNS: { id: string; label: string; color: string; dot: string }[] = [
  { id: "applied",      label: "Applied",      color: "border-blue-700/40 bg-blue-950/10",      dot: "bg-blue-500" },
  { id: "interviewing", label: "Interviewing",  color: "border-violet-700/40 bg-violet-950/10",  dot: "bg-violet-500" },
  { id: "offered",      label: "Offered",       color: "border-emerald-700/40 bg-emerald-950/10", dot: "bg-emerald-500" },
  { id: "rejected",     label: "Rejected",      color: "border-red-900/40 bg-red-950/10",        dot: "bg-red-700" },
];

function ScoreBadge({ score }: { score?: number | null }) {
  if (!score) return null;
  const color = score >= 70 ? "text-emerald-400 border-emerald-700/40" :
    score >= 50 ? "text-yellow-400 border-yellow-700/40" : "text-red-400 border-red-700/40";
  return (
    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full border ${color}`}>
      {score}%
    </span>
  );
}

function AppCard({ app, onDragStart }: { app: any; onDragStart: (e: React.DragEvent, id: string) => void }) {
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [notes, setNotes] = useState(app.notes || "");
  const [nextAction, setNextAction] = useState(app.next_action || "");
  const [nextDate, setNextDate] = useState(
    app.next_action_date ? app.next_action_date.slice(0, 10) : ""
  );

  const { mutate: save, isPending: saving } = useMutation({
    mutationFn: () =>
      updateApplication(app.id, {
        notes: notes || undefined,
        next_action: nextAction || undefined,
        next_action_date: nextDate || undefined,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  const { mutate: moveStatus } = useMutation({
    mutationFn: (status: string) => updateApplication(app.id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  const { mutate: remove } = useMutation({
    mutationFn: () => deleteApplication(app.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, app.id)}
      className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden cursor-grab active:cursor-grabbing select-none hover:border-gray-700 transition-colors"
    >
      <div className="p-3">
        <div className="flex items-start gap-2">
          <GripVertical size={12} className="text-gray-700 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-1">
              <p className="text-xs font-semibold text-white leading-tight">{app.job_title}</p>
              <ScoreBadge score={app.job_score} />
            </div>
            <p className="text-[11px] text-gray-500 truncate">{app.job_company}</p>
            {app.applied_at && (
              <p className="text-[10px] text-gray-700 mt-1">
                Applied {format(parseISO(app.applied_at), "d MMM")}
              </p>
            )}
            {app.next_action && (
              <p className="text-[10px] text-indigo-400 mt-0.5 truncate">→ {app.next_action}</p>
            )}
          </div>
        </div>
        <button
          onClick={() => setExpanded((v) => !v)}
          className="w-full flex items-center justify-center gap-1 mt-2 text-[10px] text-gray-600 hover:text-gray-400 transition-colors"
        >
          {expanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
          {expanded ? "Less" : "Details"}
        </button>
      </div>

      {expanded && (
        <div className="border-t border-gray-800 p-3 space-y-3">
          <div>
            <label className="text-[10px] text-gray-600 uppercase tracking-wide block mb-1">Next action</label>
            <input
              type="text"
              value={nextAction}
              onChange={(e) => setNextAction(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs outline-none focus:border-indigo-500"
              placeholder="e.g. Send follow-up email…"
            />
          </div>
          <div>
            <label className="text-[10px] text-gray-600 uppercase tracking-wide block mb-1">Date</label>
            <input
              type="date"
              value={nextDate}
              onChange={(e) => setNextDate(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="text-[10px] text-gray-600 uppercase tracking-wide block mb-1">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs outline-none focus:border-indigo-500 resize-none"
              placeholder="Notes…"
            />
          </div>
          {/* Move status — handy on mobile where drag-and-drop doesn't work */}
          <div className="flex items-center gap-1.5">
            <ArrowRightLeft size={10} className="text-gray-600 shrink-0" />
            <select
              value={app.status}
              onChange={(e) => moveStatus(e.target.value)}
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs outline-none focus:border-indigo-500"
            >
              {COLUMNS.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select>
          </div>

          <div className="flex gap-2 items-center">
            <button
              onClick={() => save()}
              disabled={saving}
              className="flex items-center gap-1 text-xs bg-indigo-600 hover:bg-indigo-500 px-2.5 py-1.5 rounded-lg disabled:opacity-50"
            >
              {saving ? <Loader2 size={10} className="animate-spin" /> : null}
              Save
            </button>
            {app.job_url && (
              <a
                href={app.job_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs bg-gray-800 hover:bg-gray-700 px-2.5 py-1.5 rounded-lg"
              >
                <ExternalLink size={10} /> Job
              </a>
            )}
            <button
              onClick={() => remove()}
              className="ml-auto text-red-600 hover:text-red-400 transition-colors"
              title="Remove"
            >
              <Trash2 size={12} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Applications() {
  const qc = useQueryClient();
  const [dragId, setDragId] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState<string | null>(null);

  const { data: apps = [], isLoading } = useQuery({
    queryKey: ["applications"],
    queryFn: () => listApplications().then((r) => r.data),
  });

  const { mutate: moveApp } = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      updateApplication(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  function handleDragStart(e: React.DragEvent, id: string) {
    setDragId(id);
    e.dataTransfer.effectAllowed = "move";
  }

  function handleDrop(e: React.DragEvent, colId: string) {
    e.preventDefault();
    if (dragId) {
      const app = (apps as any[]).find((a: any) => a.id === dragId);
      if (app && app.status !== colId) {
        moveApp({ id: dragId, status: colId });
      }
    }
    setDragId(null);
    setDragOver(null);
  }

  const total = (apps as any[]).length;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20 text-gray-500 text-sm gap-2">
        <Loader2 size={16} className="animate-spin" /> Loading…
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="shrink-0 px-4 md:px-6 py-4 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <LayoutDashboard size={16} className="text-indigo-400" />
          <div>
            <h2 className="text-lg font-semibold">Applications</h2>
            <p className="text-xs text-gray-500">
              {total === 0 ? "No applications yet" : `${total} tracked — drag cards or tap Details to move`}
            </p>
          </div>
        </div>
      </div>

      {total === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-gray-600 py-16">
            <LayoutDashboard size={40} className="mx-auto mb-3 opacity-20" />
            <p className="text-sm font-medium mb-1">No applications yet</p>
            <p className="text-xs">Click "Track" on any job to add it here</p>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-x-auto overflow-y-hidden">
          <div className="flex gap-3 h-full p-4 md:p-6 min-w-max">
            {COLUMNS.map((col) => {
              const colApps = (apps as any[]).filter((a: any) => a.status === col.id);
              const isDragTarget = dragOver === col.id;
              return (
                <div
                  key={col.id}
                  className={`flex flex-col w-64 rounded-xl border transition-all ${col.color} ${
                    isDragTarget ? "ring-2 ring-indigo-500/50 scale-[1.01]" : ""
                  }`}
                  onDragOver={(e) => { e.preventDefault(); setDragOver(col.id); }}
                  onDragLeave={() => setDragOver(null)}
                  onDrop={(e) => handleDrop(e, col.id)}
                >
                  <div className="shrink-0 flex items-center gap-2 px-3 py-2.5 border-b border-gray-800/50">
                    <div className={`w-2 h-2 rounded-full ${col.dot}`} />
                    <p className="text-xs font-semibold text-gray-300">{col.label}</p>
                    <span className="ml-auto text-[10px] text-gray-600 bg-gray-800 px-1.5 py-0.5 rounded-full">
                      {colApps.length}
                    </span>
                  </div>
                  <div className="flex-1 overflow-y-auto p-2 space-y-2 min-h-[80px]">
                    {colApps.map((app: any) => (
                      <AppCard key={app.id} app={app} onDragStart={handleDragStart} />
                    ))}
                    {colApps.length === 0 && (
                      <div className={`h-16 rounded-lg border-2 border-dashed flex items-center justify-center text-[10px] transition-colors ${
                        isDragTarget ? "border-indigo-500/60 text-indigo-400" : "border-gray-800 text-gray-700"
                      }`}>
                        {isDragTarget ? "Drop here" : "Empty"}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
