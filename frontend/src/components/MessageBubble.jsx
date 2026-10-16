import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "../api/client";

function Attachment({ url }) {
  const [src, setSrc] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let live = true, objectUrl;
    setSrc(null); setError(false);
    if (url.startsWith("/images/")) {
      api.get(url, { responseType: "blob" }).then(r => {
        if (live) { objectUrl = URL.createObjectURL(r.data); setSrc(objectUrl); }
      }).catch(() => { if (live) setError(true); });
    } else setSrc(url);
    return () => { live = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [url]);
  if (error) return <p className="text-xs text-red-600 mb-3">Image could not be loaded.</p>;
  if (!src) return <p className="text-xs text-muted mb-3">Loading image...</p>;
  return <a href={src} target="_blank" rel="noreferrer"><img src={src} alt="Conversation image" className="rounded-2xl mb-4 max-h-[480px] max-w-full object-contain" /></a>;
}

export default function MessageBubble({ role, content, imageUrl, streaming, sources = [], onRemember }) {
  const isUser = role === "user";
  const [copied, setCopied] = useState(false);
  const webCount = sources.filter(source => source.kind === "web").length;
  return <article className={`mb-8 flex ${isUser ? "justify-end" : "gap-3 sm:gap-4"}`}>
    {!isUser && <span className="brand-mark small mt-1 shrink-0" aria-hidden="true">a</span>}
    <div className={isUser ? "max-w-[88%] rounded-3xl rounded-tr-md bg-[#f0f0f4] px-5 py-3" : "min-w-0 flex-1 pt-1"}>
      {imageUrl && <Attachment url={imageUrl} />}
      <div className={`prose prose-sm max-w-none break-words prose-p:leading-7 prose-p:my-2 prose-headings:text-text prose-strong:text-text prose-a:text-accent prose-pre:bg-[#f5f5f8] prose-pre:text-text prose-pre:border prose-pre:border-line prose-pre:rounded-xl prose-code:before:content-none prose-code:after:content-none prose-code:text-accent prose-table:text-xs ${isUser ? "whitespace-pre-wrap" : ""}`}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content || " "}</ReactMarkdown>
        {streaming && <span className="stream-cursor text-accent">▋</span>}
      </div>
      {sources.length > 0 && <details className="mt-4 rounded-xl border border-line p-3 text-xs"><summary className="cursor-pointer font-medium text-muted">{sources.length} {webCount === sources.length ? "web" : webCount ? "web & document" : "document"} source{sources.length > 1 ? "s" : ""}</summary><div className="mt-3 space-y-3">{sources.map(s => <div key={`${s.kind || "document"}-${s.number}`}>
        {s.kind === "web" ? <><a href={s.url} target="_blank" rel="noopener noreferrer" className="font-medium text-accent hover:underline">[{s.number}] {s.title || s.url} ↗</a><p className="text-[10px] text-muted mt-1 break-all">{s.url}{s.published_date ? ` · ${s.published_date}` : ""}</p></> : <p className="font-medium">[{s.number}] {s.filename} · passage {s.chunk_index + 1}</p>}
        <p className="text-muted mt-1 leading-relaxed">{s.excerpt}...</p></div>)}</div></details>}
      {!streaming && <div className="flex gap-3 mt-2 text-[11px] text-muted">
        <button onClick={async () => { try { await navigator.clipboard.writeText(content); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { setCopied(false); } }}>{copied ? "Copied" : "Copy"}</button>
        {isUser && onRemember && content.length <= 1000 && <button onClick={() => onRemember(content)}>Save to memory</button>}
      </div>}
    </div>
  </article>;
}
