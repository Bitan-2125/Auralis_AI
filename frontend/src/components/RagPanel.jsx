import React, { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

export default function RagPanel({ chatId, useRag, onToggleRag, disabled }) {
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const fileInput = useRef(null);
  useEffect(() => {
    let live = true;
    setDocs([]); setError("");
    if (chatId) api.get(`/chats/${chatId}/documents`).then(r => { if (live) setDocs(r.data); }).catch(() => { if (live) setError("Could not load documents."); });
    return () => { live = false; };
  }, [chatId]);
  async function upload(e) {
    const file = e.target.files?.[0];
    if (!file || !chatId) return;
    if (file.size > 4 * 1024 * 1024) { setError("File too large (4 MB limit)."); e.target.value = ""; return; }
    setUploading(true); setError("");
    try {
      const form = new FormData(); form.append("file", file);
      const { data } = await api.post(`/chats/${chatId}/documents`, form);
      setDocs(d => [...d, data]); await onToggleRag(true);
    } catch (err) { setError(err?.response?.data?.detail || "Document upload failed."); }
    finally { setUploading(false); if (fileInput.current) fileInput.current.value = ""; }
  }
  async function remove(id) {
    setError("");
    try { await api.delete(`/chats/${chatId}/documents/${id}`); setDocs(d => d.filter(x => x.id !== id)); }
    catch { setError("Could not delete document."); }
  }
  return <div className="space-y-5">
    <p className="text-xs text-muted leading-relaxed">Attach reference material and ask questions about it. Relevant passages are included with your question and shown as sources.</p>
    <label className="flex gap-2 items-center text-sm"><input type="checkbox" checked={useRag} disabled={disabled} onChange={e => onToggleRag(e.target.checked)} className="accent-accent" /> Use documents in answers</label>
    <button onClick={() => fileInput.current?.click()} disabled={!chatId || uploading || disabled} className="panel-button w-full">{uploading ? "Reading document..." : "+ Upload a document"}</button>
    <input ref={fileInput} type="file" hidden accept=".pdf,.docx,.txt,.md,.csv" onChange={upload} />
    <p className="text-[11px] text-muted">PDF, DOCX, TXT, MD, CSV · 4 MB per file · 20 files per chat. Scanned PDFs need OCR.</p>
    {error && <p role="alert" className="text-xs text-red-600">{error}</p>}
    {!docs.length && <p className="text-sm text-muted py-8 text-center">No documents attached yet.</p>}
    {docs.map(doc => <div key={doc.id} className="border border-line rounded-xl p-3"><div className="flex gap-2 items-center"><p className="truncate flex-1 text-xs font-medium" title={doc.filename}>{doc.filename}</p><button aria-label={`Remove ${doc.filename}`} disabled={disabled} onClick={() => remove(doc.id)} className="text-muted">×</button></div><p className="text-[10px] text-muted mt-2">{doc.chunk_count} indexed passages</p></div>)}
  </div>;
}
