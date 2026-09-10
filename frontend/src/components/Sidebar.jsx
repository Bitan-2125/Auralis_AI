import React from "react";
import { useNavigate } from "react-router-dom";

export default function Sidebar({ chats, activeChatId, onNewChat, onSelectChat, onDeleteChat }) {
  const navigate = useNavigate();

  return (
    <aside className="w-64 shrink-0 bg-panel border-r border-line flex flex-col h-screen">
      <div className="p-4 border-b border-line">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate("/")}>
            <span className="w-2.5 h-2.5 rounded-full bg-signal animate-pulse"></span>
            <span className="font-mono text-xs tracking-widest text-text font-bold uppercase">Auralis AI</span>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 bg-accent/20 text-accent border border-accent/40 rounded">
            Free Access
          </span>
        </div>
        <button
          onClick={onNewChat}
          className="w-full bg-accent hover:bg-accent/90 text-white text-sm font-medium rounded py-2 transition-colors flex items-center justify-center gap-2 shadow-sm shadow-accent/20"
        >
          <span className="text-base font-bold">+</span> New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {chats.length === 0 && (
          <p className="text-xs text-muted px-4 py-6 text-center">No chats yet. Start one above.</p>
        )}
        {chats.map((chat) => (
          <div
            key={chat.id}
            onClick={() => { onSelectChat(chat.id); navigate(`/chat/${chat.id}`); }}
            className={`group flex items-center justify-between px-4 py-2.5 cursor-pointer text-sm border-l-2 transition-colors ${
              chat.id === activeChatId
                ? "bg-panel2 border-accent text-text font-medium"
                : "border-transparent text-muted hover:bg-panel2/60 hover:text-text"
            }`}
          >
            <span className="truncate">{chat.title || "New chat"}</span>
            <button
              onClick={(e) => { e.stopPropagation(); onDeleteChat(chat.id); }}
              className="opacity-0 group-hover:opacity-100 text-muted hover:text-red-400 text-xs ml-2 shrink-0 p-1"
              title="Delete chat"
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      <div className="p-3 border-t border-line bg-panel2/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <div className="text-[11px] leading-tight">
              <p className="text-text font-medium">AgentRouter & Groq</p>
              <p className="text-muted text-[10px]">All models unlocked</p>
            </div>
          </div>
          <span className="text-[10px] font-mono text-signal bg-signal/10 px-1.5 py-0.5 rounded border border-signal/20">
            ONLINE
          </span>
        </div>
      </div>
    </aside>
  );
}
