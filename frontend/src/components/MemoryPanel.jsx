import React, { useEffect, useState } from "react";
import { api } from "../api/client";
export default function MemoryPanel({ enabled, onToggle, revision, disabled }) {
  const [memories, setMemories] = useState([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { let live = true; api.get("/memories").then(r => { if (live) setMemories(r.data); }).catch(() => { if (live) setError("Could not load memory."); }); return () => { live = false; }; }, [revision]);
  async function add(e) {
    e.preventDefault(); if (!input.trim()) return; setBusy(true); setError("");
    try { const { data } = await api.post("/memories", { content: input }); setMemories(m => [data, ...m.filter(x => x.id !== data.id)]); setInput(""); }
    catch (err) { setError(err?.response?.data?.detail || "Could not save memory."); }
    finally { setBusy(false); }
  }
  async function remove(id) {
    try { await api.delete(`/memories/${id}`); setMemories(m => m.filter(x => x.id !== id)); }
    catch { setError("Could not delete memory."); }
  }
  return <div className="space-y-5">
    <p className="text-xs text-muted leading-relaxed">Save preferences or facts to use across conversations. Only details you explicitly save are added here.</p>
    <label className="flex gap-2 items-center text-sm"><input type="checkbox" className="accent-accent" checked={enabled} disabled={disabled} onChange={e => onToggle(e.target.checked)} /> Use saved memory</label>
    <form onSubmit={add} className="space-y-2"><textarea aria-label="New memory" rows={3} maxLength={1000} value={input} onChange={e => setInput(e.target.value)} placeholder="I prefer concise answers with Python examples." className="w-full border border-line rounded-xl bg-white p-3 text-xs resize-none" /><button disabled={disabled || busy || !input.trim()} className="panel-button w-full">{busy ? "Saving..." : "Save memory"}</button></form>
    <p className="text-[11px] text-muted">You can also send "Remember: I prefer short answers" in chat. Turning memory off stops using it; it does not delete it.</p>
    {error && <p role="alert" className="text-xs text-red-600">{error}</p>}
    {!memories.length && <p className="py-5 text-sm text-center text-muted">No saved memories yet.</p>}
    {memories.map(m => <div key={m.id} className="border border-line rounded-xl p-3 flex gap-2"><p className="flex-1 text-xs leading-relaxed whitespace-pre-wrap break-words">{m.content}</p><button aria-label="Delete memory" disabled={disabled} onClick={() => remove(m.id)} className="text-muted self-start">×</button></div>)}
  </div>;
}
