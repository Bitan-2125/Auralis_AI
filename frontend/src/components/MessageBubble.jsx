import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MessageBubble({ role, content, imageUrl, streaming }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[75%] rounded-md px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-accent text-white rounded-br-sm"
            : "bg-panel border border-line text-text rounded-bl-sm shadow-sm"
        }`}
      >
        {imageUrl && (
          <img src={imageUrl} alt="attachment" className="rounded-sm mb-2 max-h-64 object-cover" />
        )}
        <div className={`prose prose-sm max-w-none
          prose-p:my-1 prose-p:leading-relaxed
          prose-headings:font-semibold prose-headings:text-text prose-headings:mt-3 prose-headings:mb-1
          prose-h1:text-lg prose-h2:text-base prose-h3:text-sm
          prose-strong:text-text prose-strong:font-semibold
          prose-em:text-muted
          prose-code:bg-panel2 prose-code:text-accent prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:font-mono prose-code:before:content-none prose-code:after:content-none
          prose-pre:bg-panel2 prose-pre:border prose-pre:border-line prose-pre:rounded-md prose-pre:p-3 prose-pre:overflow-x-auto
          prose-pre:text-text prose-pre:text-xs
          prose-ul:my-1 prose-ul:pl-4 prose-li:my-0.5
          prose-ol:my-1 prose-ol:pl-4
          prose-blockquote:border-l-4 prose-blockquote:border-accent prose-blockquote:pl-3 prose-blockquote:text-muted prose-blockquote:italic prose-blockquote:my-2
          prose-a:text-accent prose-a:underline
          prose-hr:border-line
          prose-table:text-xs prose-thead:bg-panel2 prose-th:px-3 prose-th:py-1.5 prose-td:px-3 prose-td:py-1.5 prose-table:border prose-table:border-line
          ${isUser ? "prose-invert prose-p:text-white prose-strong:text-white prose-headings:text-white prose-code:bg-white/20 prose-code:text-white" : ""}
        `}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content || " "}</ReactMarkdown>
        </div>
        {streaming && <span className="stream-cursor text-muted">▍</span>}
      </div>
    </div>
  );
}
