import React from "react";

export default function ModelSelector({ models, value, onChange }) {
  const current = models.find((m) => m.id === value);
  const agentrouterModels = models.filter((m) => m.provider === "AgentRouter");
  const groqModels = models.filter((m) => m.provider !== "AgentRouter");

  return (
    <div className="flex items-center gap-2">
      {current && (
        <span
          className={`text-[11px] font-mono px-2 py-0.5 rounded border ${
            current.provider === "AgentRouter"
              ? "bg-purple-950/40 text-purple-300 border-purple-800/60"
              : "bg-emerald-950/40 text-emerald-300 border-emerald-800/60"
          }`}
        >
          {current.provider === "AgentRouter" ? "⚡ AgentRouter" : "🚀 Groq"}
        </span>
      )}
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="appearance-none bg-panel2 border border-line hover:border-accent/60 rounded px-3 pr-8 py-1.5 text-xs font-mono text-text focus:border-accent outline-none cursor-pointer shadow-sm transition-colors"
        >
          {agentrouterModels.length > 0 && (
            <optgroup label="── AgentRouter Models ──" className="bg-panel font-sans font-semibold text-accent">
              {agentrouterModels.map((m) => (
                <option key={m.id} value={m.id} className="bg-panel2 text-text font-mono">
                  {m.name || m.id}
                </option>
              ))}
            </optgroup>
          )}

          {groqModels.length > 0 && (
            <optgroup label="── Groq Ultra-Fast Models ──" className="bg-panel font-sans font-semibold text-emerald-400">
              {groqModels.map((m) => (
                <option key={m.id} value={m.id} className="bg-panel2 text-text font-mono">
                  {m.id}{m.supports_vision ? " (vision)" : ""}
                </option>
              ))}
            </optgroup>
          )}
        </select>
        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-muted text-xs">
          ▼
        </div>
      </div>
      {current?.supports_vision && (
        <span className="text-[10px] uppercase tracking-wide text-signal font-mono bg-signal/10 px-1.5 py-0.5 rounded border border-signal/30">
          vision
        </span>
      )}
    </div>
  );
}
