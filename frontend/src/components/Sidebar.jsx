import React from "react";
import { useNavigate } from "react-router-dom";

export default function Sidebar({ chats, activeChatId, onNewChat, onSelectChat, onDeleteChat, user, onLogout }) {
  const navigate = useNavigate();

  return (
    <aside className="w-64 shrink-0 bg-panel border-r border-line flex flex-col h-screen">
      <div className="p-4 border-b border-line">
        <div className="flex items-center gap-2 mb-4">
          <span className="w-2 h-2 rounded-full bg-signal"></span>
          <span className="font-mono text-[11px] tracking-widest text-muted uppercase">Auralis AI</span>
        </div>
        <button
          onClick={onNewChat}
          className="w-full bg-accent hover:bg-accent/90 text-white text-sm font-medium rounded-sm py-2 transition-colors"
        >
          + New chat
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
                ? "bg-panel2 border-accent text-text"
                : "border-transparent text-muted hover:bg-panel2/60 hover:text-text"
            }`}
          >
            <span className="truncate">{chat.title || "New chat"}</span>
            <button
              onClick={(e) => { e.stopPropagation(); onDeleteChat(chat.id); }}
              className="opacity-0 group-hover:opacity-100 text-muted hover:text-red-400 text-xs ml-2 shrink-0"
              title="Delete chat"
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      <div className="p-4 border-t border-line flex items-center justify-between">
        <div className="text-xs">
          <p className="text-text truncate max-w-[140px]">{user?.full_name || user?.email}</p>
          <p className="text-muted truncate max-w-[140px]">{user?.email}</p>
        </div>
        <button onClick={onLogout} className="text-xs text-muted hover:text-red-400" title="Sign out">
          Sign out
        </button>
      </div>
    </aside>
  );
}
