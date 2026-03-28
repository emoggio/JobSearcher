import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { uploadCV, getCurrentCV, listCVs, activateCV, deleteCVFile, clearScores } from "../api";
import { Upload, CheckCircle, Trash2, RefreshCw, FileText, Star, AlertTriangle, Loader2 } from "lucide-react";

export default function CV() {
  const qc = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null); // filename or "parsed"

  const { data: cv } = useQuery({
    queryKey: ["cv"],
    queryFn: () => getCurrentCV().then((r) => r.data),
    retry: false,
  });

  const { data: cvList } = useQuery({
    queryKey: ["cv-list"],
    queryFn: () => listCVs().then((r) => r.data),
    retry: false,
  });

  const { mutate: upload, isPending: uploading } = useMutation({
    mutationFn: (file: File) => uploadCV(file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cv"] });
      qc.invalidateQueries({ queryKey: ["cv-list"] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const { mutate: activate, isPending: activating, variables: activatingFile } = useMutation({
    mutationFn: (filename: string) => activateCV(filename),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cv"] });
      qc.invalidateQueries({ queryKey: ["cv-list"] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const { mutate: removeFile, isPending: deletingFile, variables: deletingFilename } = useMutation({
    mutationFn: (filename: string) => deleteCVFile(filename),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cv"] });
      qc.invalidateQueries({ queryKey: ["cv-list"] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
      setConfirmDelete(null);
    },
  });

  const { mutate: resetScores, isPending: resetting } = useMutation({
    mutationFn: () => clearScores(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });

  function handleFiles(files: FileList | null) {
    if (files?.[0]) upload(files[0]);
  }

  const files: any[] = cvList?.files || [];

  return (
    <div className="p-6 space-y-6 max-w-2xl mx-auto">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Your CV</h2>
        {cv && (
          <button
            onClick={() => resetScores()}
            disabled={resetting}
            title="Re-score all jobs with Claude using this CV"
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw size={12} className={resetting ? "animate-spin" : ""} />
            Re-score jobs
          </button>
        )}
      </div>

      {/* Upload zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          dragOver ? "border-indigo-500 bg-indigo-950/30" : "border-gray-700 hover:border-gray-600"
        }`}
      >
        <input ref={inputRef} type="file" accept=".pdf" className="hidden" onChange={(e) => handleFiles(e.target.files)} />
        {uploading ? (
          <div className="flex flex-col items-center gap-2 text-gray-400">
            <Loader2 size={28} className="animate-spin" />
            <p className="text-sm">Parsing CV…</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 text-gray-500">
            <Upload size={28} />
            <p className="text-sm">Drop a PDF CV here or click to browse</p>
            <p className="text-xs text-gray-700">You can upload multiple variants</p>
          </div>
        )}
      </div>

      {/* Uploaded CVs list */}
      {files.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">Uploaded CVs</p>
          {files.map((f: any) => (
            <div
              key={f.filename}
              className={`flex items-center gap-3 p-3 rounded-xl border transition-colors ${
                f.is_active
                  ? "border-indigo-600/50 bg-indigo-950/15"
                  : "border-gray-800 bg-gray-900"
              }`}
            >
              <FileText size={16} className={f.is_active ? "text-indigo-400" : "text-gray-600"} />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white truncate">{f.filename}</p>
                <p className="text-xs text-gray-600">{f.size_kb} KB</p>
              </div>
              {f.is_active && (
                <span className="flex items-center gap-1 text-[10px] text-indigo-400 bg-indigo-950/40 border border-indigo-800/40 px-2 py-0.5 rounded-full shrink-0">
                  <Star size={9} /> Active
                </span>
              )}
              {!f.is_active && (
                <button
                  onClick={() => activate(f.filename)}
                  disabled={activating && activatingFile === f.filename}
                  className="flex items-center gap-1 text-xs px-2.5 py-1 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50 shrink-0"
                >
                  {activating && activatingFile === f.filename
                    ? <Loader2 size={10} className="animate-spin" />
                    : <RefreshCw size={10} />
                  }
                  Use this
                </button>
              )}
              {confirmDelete === f.filename ? (
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => removeFile(f.filename)}
                    disabled={deletingFile && deletingFilename === f.filename}
                    className="text-xs px-2 py-1 bg-red-700 hover:bg-red-600 rounded-lg"
                  >
                    Delete
                  </button>
                  <button onClick={() => setConfirmDelete(null)} className="text-xs px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded-lg">
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmDelete(f.filename)}
                  className="text-gray-700 hover:text-red-400 transition-colors shrink-0"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Parsed profile */}
      {cv && (
        <div className="space-y-4">
          <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">Active CV profile</p>
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
