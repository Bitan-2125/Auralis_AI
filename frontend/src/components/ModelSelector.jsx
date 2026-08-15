import React from "react";

export default function ModelSelector({ models, value, onChange }) {
  const current = models.find((m) => m.id === value);
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none bg-panel2 border border-line rounded-sm pl-3 pr-8 py-1.5 text-xs font-mono text-text focus:border-accent outline-none cursor-pointer"
      >
        {models.map((m) => (
          <option key={m.id} value={m.id}>
            {m.id}{m.supports_vision ? " (vision)" : ""}
          </option>
        ))}
      </select>
      {current?.supports_vision && (
        <span className="ml-2 text-[10px] uppercase tracking-wide text-signal font-mono">vision</span>
      )}
    </div>
  );
}
