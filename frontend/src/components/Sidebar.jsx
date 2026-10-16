import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function Sidebar({ chats, activeChatId, onNewChat, onDeleteChat, onRenameChat, disabled, open, onClose }) {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [search, setSearch] = useState("");
  const filtered = chats.filter(c => c.title.toLowerCase().includes(search.toLowerCase()));
  return <>
    {open && <button className="fixed inset-0 bg-black/30 z-20 md:hidden" aria-label="Close sidebar" onClick={onClose} />}
    <aside className={`${open ? "flex" : "hidden"} md:flex fixed md:static inset-y-0 left-0 z-30 w-64 shrink-0 flex-col bg-[#f7f7f8] border-r border-line/60`}>
      <div className="px-5 pt-6 pb-4">
        <div className="flex items-center justify-between mb-7"><a href="/chat" className="flex gap-2 items-center font-display font-semibold text-lg"><span className="brand-mark">a</span> auralis<span className="text-accent">.</span></a><button className="md:hidden text-muted" onClick={onClose} aria-label="Close sidebar">×</button></div>
        <button onClick={onNewChat} disabled={disabled} className="w-full flex items-center justify-between bg-white border border-line rounded-xl px-3 py-2.5 text-sm shadow-sm disabled:opacity-40 hover:border-accent"><span>New conversation</span><span className="text-xl leading-none">+</span></button>
        <input aria-label="Search conversations" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search conversations..." className="mt-4 w-full bg-transparent text-xs p-2 outline-none rounded-lg border border-transparent focus:border-line" />
      </div>
      <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted px-6 mb-2">Your conversations</div>
      <nav className="flex-1 overflow-y-auto px-3 pb-4" aria-label="Conversation history">
        {!filtered.length && <p className="px-3 py-5 text-xs text-muted">{search ? "No matching conversations." : "Your chats will appear here."}</p>}
        {filtered.map(chat => <div key={chat.id} className={`group flex items-center rounded-lg mb-1 ${chat.id === activeChatId ? "bg-[#e9e9ed]" : "hover:bg-[#ededf0]"}`}>
          <button disabled={disabled} onClick={() => { navigate(`/chat/${chat.id}`); onClose(); }} className="text-left truncate flex-1 min-w-0 px-3 py-3 text-[13px] disabled:opacity-60">{chat.title}</button>
          <button aria-label={`Rename ${chat.title}`} disabled={disabled} onClick={() => onRenameChat(chat)} className="history-action" title="Rename">✎</button>
          <button aria-label={`Delete ${chat.title}`} disabled={disabled} onClick={() => onDeleteChat(chat.id)} className="history-action mr-1" title="Delete">×</button>
        </div>)}
      </nav>
      <div className="border-t border-line/60 p-4"><div className="flex items-center gap-3"><div className="w-8 h-8 rounded-full bg-accent/10 text-accent flex items-center justify-center text-sm font-medium">{(user?.full_name || user?.email || "U")[0].toUpperCase()}</div><div className="min-w-0 flex-1"><p className="text-xs font-medium truncate">{user?.full_name || user?.email}</p><p className="text-[10px] text-muted mt-0.5">Personal workspace</p></div><button onClick={() => { logout(); navigate("/login"); }} title="Sign out" aria-label="Sign out" className="text-muted text-sm">↗</button></div></div>
    </aside>
  </>;
}
