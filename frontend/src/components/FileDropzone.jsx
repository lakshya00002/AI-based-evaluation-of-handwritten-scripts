import { useCallback, useState } from "react";

export default function FileDropzone({ onFiles, multiple = false, accept = "image/*,.pdf" }) {
  const [drag, setDrag] = useState(false);

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDrag(false);
      const files = e.dataTransfer?.files;
      if (files?.length) onFiles(multiple ? Array.from(files) : [files[0]]);
    },
    [multiple, onFiles]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={onDrop}
      className={`border-2 border-dashed rounded-2xl p-10 text-center transition-colors ${
        drag ? "border-accent bg-blue-50" : "border-slate-300 bg-white"
      }`}
    >
      <p className="text-slate-600 mb-4">Drag & drop {multiple ? "files" : "a file"} here, or browse</p>
      <label className="inline-block px-4 py-2 bg-accent text-white rounded-lg cursor-pointer hover:bg-accent-dim">
        Choose file
        <input
          type="file"
          className="hidden"
          accept={accept}
          multiple={multiple}
          onChange={(e) => {
            const f = e.target.files;
            if (f?.length) onFiles(multiple ? Array.from(f) : [f[0]]);
          }}
        />
      </label>
    </div>
  );
}
