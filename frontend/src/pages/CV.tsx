import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { uploadCV, getCurrentCV, deleteCV, clearScores } from "../api";
import { Upload, CheckCircle, Trash2, RefreshCw, AlertTriangle } from "lucide-react";

export default function CV() {
  const qc = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: cv } = useQuery({
    queryKey: ["cv"],
    queryFn: () => getCurrentCV().then((r) => r.data),
    retry: false,
  });

  const { mutate: upload, isPending, isSuccess } = useMutation({
    mutationFn: (file: File) => uploadCV(file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cv"] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const { mutate: removeCv, isPending: deleting } = useMutation({
    mutationFn: () => deleteCV(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cv"] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
      setConfirmDelete(false);
    },
  });

  const { mutate: resetScores, isPending: resetting } = useMutation({
    mutationFn: () => clearScores(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });

  function handleFiles(files: FileList | null) {
    if (files?.[0]) upload(files[0]);
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl mx-auto">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Your CV</h2>
        {cv && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => resetScores()}
              disabled={resetting}
              title="Re-score all jobs with Claude using this CV"
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw size={12} className={resetting ? "animate-spin" : ""} />
              Re-score jobs
            </button>
            <button
              onClick={() => setConfirmDelete(true)}
              title="Delete CV and start fresh"
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-red-900/30 hover:bg-red-900/50 text-red-400 border border-red-800/40 rounded-lg transition-colors"
            >
              <Trash2 size={12} />
              Delete CV
            </button>
          </div>
        )}
      </div>

      {/* Confirm delete dialog */}
      {confirmDelete && (
        <div className="bg-red-950/30 border border-red-800/50 rounded-xl p-4 space-y-3">
          <div className="flex items-center gap-2 text-red-400">
            <AlertTriangle size={14} />
            <p className="text-sm font-medium">Delete your CV?</p>
          </div>
          <p className="text-xs text-gray-400">This will remove your parsed profile. Scores will remain until you clear them. Upload a new CV to re-analyse.</p>
          <div className="flex gap-2">
            <button
              onClick={() => removeCv()}
              disabled={deleting}
              className="text-xs px-3 py-1.5 bg-red-700 hover:bg-red-600 rounded-lg transition-colors"
            >
              {deleting ? "Deleting…" : "Yes, delete"}
            </button>
            <button
              onClick={() => setConfirmDelete(false)}
              className="text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Upload zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
          dragOver ? "border-indigo-500 bg-indigo-950/30" : "border-gray-700 hover:border-gray-600"
        }`}
      >
        <input ref={inputRef} type="file" accept=".pdf" className="hidden" onChange={(e) => handleFiles(e.target.files)} />
        {isPending ? (
          <p className="text-gray-400 text-sm">Parsing CV…</p>
        ) : isSuccess ? (
          <div className="flex flex-col items-center gap-2 text-emerald-400">
            <CheckCircle size={28} />
            <p className="text-sm">CV uploaded and parsed</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 text-gray-500">
            <Upload size={28} />
            <p className="text-sm">{cv ? "Drop a new PDF to replace your CV" : "Drop your PDF CV here or click to browse"}</p>
          </div>
        )}
      </div>

      {/* Parsed profile */}
      {cv && (
        <div className="space-y-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h3 className="font-semibold mb-1">{cv.name}</h3>
            <p className="text-sm text-gray-400">{cv.email} {cv.phone && `· ${cv.phone}`}</p>
            {cv.summary && <p className="mt-3 text-sm text-gray-300 leading-relaxed">{cv.summary}</p>}
          </div>

          {cv.skills?.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h4 className="text-sm font-medium text-gray-400 mb-3">Skills</h4>
              <div className="flex flex-wrap gap-2">
                {cv.skills.map((s: string) => (
                  <span key={s} className="text-xs bg-gray-800 text-gray-300 px-2.5 py-1 rounded-full">{s}</span>
                ))}
              </div>
            </div>
          )}

          {cv.experience?.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
              <h4 className="text-sm font-medium text-gray-400">Experience</h4>
              {cv.experience.map((exp: any, i: number) => (
                <div key={i}>
                  <p className="font-medium text-sm">{exp.title} <span className="text-gray-500">at {exp.company}</span></p>
                  <p className="text-xs text-gray-500">{exp.dates}</p>
                  {exp.bullets?.length > 0 && (
                    <ul className="mt-1.5 space-y-1">
                      {exp.bullets.map((b: string, j: number) => (
                        <li key={j} className="text-xs text-gray-400 pl-3 border-l border-gray-700">{b}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
