import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listApplications, updateApplication, deleteApplication } from "../api";
import { Trash2 } from "lucide-react";

const STATUSES = ["applied", "screen", "interview", "offer", "rejected"];

const STATUS_COLORS: Record<string, string> = {
  applied: "bg-blue-900 text-blue-300",
  screen: "bg-yellow-900 text-yellow-300",
  interview: "bg-purple-900 text-purple-300",
  offer: "bg-emerald-900 text-emerald-300",
  rejected: "bg-red-900 text-red-400",
};

export default function Applications() {
  const qc = useQueryClient();
  const { data: apps = [] } = useQuery({
    queryKey: ["applications"],
    queryFn: () => listApplications().then((r) => r.data),
  });

  const { mutate: updateStatus } = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => updateApplication(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  const { mutate: remove } = useMutation({
    mutationFn: (id: string) => deleteApplication(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  const grouped = STATUSES.reduce((acc, s) => {
    acc[s] = apps.filter((a: any) => a.status === s);
    return acc;
  }, {} as Record<string, any[]>);

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-6">Applications</h2>
      <div className="grid grid-cols-5 gap-3">
        {STATUSES.map((status) => (
          <div key={status} className="space-y-2">
            <div className="flex items-center justify-between mb-3">
              <span className={`text-xs font-medium px-2 py-1 rounded-full capitalize ${STATUS_COLORS[status]}`}>
                {status}
              </span>
              <span className="text-xs text-gray-500">{grouped[status].length}</span>
            </div>
            {grouped[status].map((app: any) => (
              <div key={app.id} className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-sm">
                <p className="text-gray-300 truncate text-xs">{app.job_id.slice(0, 8)}…</p>
                {app.notes && <p className="text-gray-500 text-xs mt-1 truncate">{app.notes}</p>}
                <div className="flex gap-1 mt-2 flex-wrap">
                  {STATUSES.filter((s) => s !== status).map((s) => (
                    <button
                      key={s}
                      onClick={() => updateStatus({ id: app.id, status: s })}
                      className="text-xs text-gray-500 hover:text-white capitalize"
                    >
                      → {s}
                    </button>
                  ))}
                </div>
                <button
                  onClick={() => remove(app.id)}
                  className="mt-2 text-gray-700 hover:text-red-400 transition-colors"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
