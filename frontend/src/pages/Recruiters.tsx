import { useQuery } from "@tanstack/react-query";
import { listRecruiters } from "../api";
import { ExternalLink, Copy } from "lucide-react";

export default function Recruiters() {
  const { data: recruiters = [] } = useQuery({
    queryKey: ["recruiters"],
    queryFn: () => listRecruiters().then((r) => r.data),
  });

  return (
    <div className="p-6 space-y-4">
      <h2 className="text-xl font-semibold">Recruiter Leads</h2>
      <p className="text-sm text-gray-400">
        Click the LinkedIn link to find the recruiter, then use the suggested message to connect.
      </p>

      {recruiters.length === 0 ? (
        <p className="text-gray-500 text-sm">No recruiter leads yet. Find recruiters from the Jobs page.</p>
      ) : (
        <div className="space-y-3">
          {recruiters.map((rec: any) => (
            <div key={rec.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <p className="font-medium text-white">{rec.company}</p>
                  <p className="text-sm text-gray-400">{rec.title}</p>
                  {rec.message_draft && (
                    <div className="mt-3 bg-gray-800 rounded-lg p-3">
                      <p className="text-xs text-gray-500 mb-1">Suggested message</p>
                      <p className="text-sm text-gray-300">{rec.message_draft}</p>
                    </div>
                  )}
                </div>
                <div className="flex gap-2 shrink-0">
                  {rec.message_draft && (
                    <button
                      onClick={() => navigator.clipboard.writeText(rec.message_draft)}
                      className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors"
                      title="Copy message"
                    >
                      <Copy size={14} />
                    </button>
                  )}
                  <a
                    href={rec.linkedin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-700 hover:bg-indigo-600 text-sm transition-colors"
                  >
                    <ExternalLink size={13} />
                    LinkedIn
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
