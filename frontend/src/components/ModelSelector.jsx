import React from "react";
export default function ModelSelector({ models, value, onChange, disabled }) {
  const groups = [...new Set(models.map(m => m.provider))];
  return <select aria-label="Chat model" value={value} onChange={e => onChange(e.target.value)} disabled={disabled || !models.length} className="bg-transparent text-sm font-medium max-w-[230px] sm:max-w-[340px] py-2 pr-2 outline-none rounded-lg disabled:opacity-50">
    {!models.some(m => m.id === value) && <option value={value}>{value ? "Choose an available model" : "Loading models..."}</option>}
    {groups.map(provider => <optgroup label={provider} key={provider}>{models.filter(m => m.provider === provider).map(m => <option key={m.id} value={m.id} disabled={!m.available}>{m.name}{m.supports_vision ? " · Vision" : ""}{!m.available ? " · API key needed" : ""}</option>)}</optgroup>)}
  </select>;
}
