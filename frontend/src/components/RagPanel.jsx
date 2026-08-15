import React, { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

export default function RagPanel({ chatId, useRag, onToggleRag }) {
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef(null);

  useEffect(() => {
    if (!chatId) return;
    api.get(`/chats/${chatId}/documents`).then((r) => setDocs(r.data)).catch(() => {});
  }, [chatId]);

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file || !chatId) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post(`/chats/${chatId}/documents`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setDocs((d) => [...d, data]);
      onToggleRag(true);
    } catch (err) {
      alert(err?.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function handleDelete(docId) {
    await api.delete(`/chats/${chatId}/documents/${docId}`);
    setDocs((d) => d.filter((x) => x.id !== docId));
  }

  return (
    <div className="border-t border-line p-3 bg-panel">
      <div className="flex items-center justify-between mb-2">
        <label className="flex items-center gap-2 text-xs text-muted cursor-pointer">
          <input
            type="checkbox"
            checked={useRag}
            onChange={(e) => onToggleRag(e.target.checked)}
            className="accent-accent"
          />
          Use RAG (answer from uploaded documents)
        </label>
        <button
          onClick={() => fileInput.current?.click()}
          disabled={uploading || !chatId}
          className="text-xs text-accent hover:underline disabled:opacity-50"
        >
          {uploading ? "Uploading..." : "+ Attach document"}
        </button>
        <input ref={fileInput} type="file" hidden accept=".pdf,.docx,.txt,.md,.csv" onChange={handleUpload} />
      </div>
      {docs.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {docs.map((d) => (
            <span key={d.id} className="flex items-center gap-1 bg-panel2 border border-line rounded-sm px-2 py-1 text-[11px] font-mono text-muted">
              {d.filename} <span className="text-signal">·{d.chunk_count}</span>
              <button onClick={() => handleDelete(d.id)} className="ml-1 hover:text-red-400">✕</button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
