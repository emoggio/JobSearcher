import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { uploadCV, getCurrentCV } from "../api";
import { Upload, CheckCircle } from "lucide-react";

export default function CV() {
  const qc = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

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

  function handleFiles(files: FileList | null) {
    if (files?.[0]) upload(files[0]);
  }

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-xl font-semibold">Your CV</h2>

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
            <p className="text-sm">Drop your PDF CV here or click to browse</p>
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
