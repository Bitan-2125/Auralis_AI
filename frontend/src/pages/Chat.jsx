import React, { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, API_URL } from "../api/client";
import { useAuth } from "../context/AuthContext.jsx";
import Sidebar from "../components/Sidebar.jsx";
import ModelSelector from "../components/ModelSelector.jsx";
import MessageBubble from "../components/MessageBubble.jsx";
import RagPanel from "../components/RagPanel.jsx";

export default function Chat() {
  const { user, token, logout } = useAuth();
  const { chatId } = useParams();
  const navigate = useNavigate();

  const [chats, setChats] = useState([]);
  const [activeChat, setActiveChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [chatModels, setChatModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [mode, setMode] = useState("chat"); // "chat" | "image"
  const bottomRef = useRef(null);

  // Load chat list + available models once.
  useEffect(() => {
    api.get("/chats").then((r) => setChats(r.data));
    api.get("/models/chat").then((r) => {
      setChatModels(r.data);
      if (r.data.length) setSelectedModel(r.data[0].id);
    });
  }, []);

  // Load the active chat + its messages whenever the route param changes.
  useEffect(() => {
    if (!chatId) {
      setActiveChat(null);
      setMessages([]);
      return;
    }
    api.get(`/chats/${chatId}`).then((r) => {
      setActiveChat(r.data);
      setSelectedModel(r.data.default_model);
    });
    api.get(`/chats/${chatId}/messages`).then((r) => setMessages(r.data));
  }, [chatId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  const handleNewChat = useCallback(async () => {
    const { data } = await api.post("/chats", { title: "New chat", default_model: selectedModel || undefined });
    setChats((c) => [data, ...c]);
    navigate(`/chat/${data.id}`);
  }, [selectedModel, navigate]);

  const handleDeleteChat = useCallback(async (id) => {
    await api.delete(`/chats/${id}`);
    setChats((c) => c.filter((x) => x.id !== id));
    if (id === chatId) navigate("/");
  }, [chatId, navigate]);

  const handleToggleRag = useCallback(async (value) => {
    if (!activeChat) return;
    await api.patch(`/chats/${activeChat.id}`, { use_rag: value });
    setActiveChat((c) => ({ ...c, use_rag: value }));
  }, [activeChat]);

  async function handleGenerateImage() {
    if (!input.trim() || !activeChat) return;
    const prompt = input;
    setInput("");
    setMessages((m) => [...m, { id: `local-${Date.now()}`, role: "user", content: prompt, created_at: new Date().toISOString() }]);
    setSending(true);
    try {
      const { data } = await api.post("/images/generate", { prompt });
      setMessages((m) => [...m, {
        id: `img-${Date.now()}`, role: "assistant", content: `Generated image for: *${prompt}*`,
        image_url: data.url, created_at: new Date().toISOString(),
      }]);
    } finally {
      setSending(false);
    }
  }

  async function handleSend() {
    if (mode === "image") return handleGenerateImage();
    if (!input.trim()) return;

    let chat = activeChat;
    if (!chat) {
      const { data } = await api.post("/chats", { title: "New chat", default_model: selectedModel });
      chat = data;
      setChats((c) => [data, ...c]);
      setActiveChat(data);
      navigate(`/chat/${data.id}`, { replace: true });
    }

    const userText = input;
    setInput("");
    setMessages((m) => [...m, { id: `local-${Date.now()}`, role: "user", content: userText, created_at: new Date().toISOString() }]);
    setSending(true);
    setStreamingText("");

    try {
      const resp = await fetch(`${API_URL}/chats/${chat.id}/messages`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content: userText, model: selectedModel }),
      });

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullText = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop();
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = JSON.parse(line.slice(6));
          if (payload.delta) {
            fullText += payload.delta;
            setStreamingText(fullText);
          } else if (payload.error) {
            fullText += `\n\n**Error:** ${payload.error}`;
            setStreamingText(fullText);
          } else if (payload.done) {
            setMessages((m) => [...m, { id: payload.message_id, role: "assistant", content: fullText, created_at: new Date().toISOString() }]);
            setStreamingText("");
          }
        }
      }
      setChats((cs) => cs.map((c) => (c.id === chat.id ? { ...c, title: userText.slice(0, 60) } : c)));
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex h-screen bg-ink">
      <Sidebar
        chats={chats}
        activeChatId={chatId}
        onNewChat={handleNewChat}
        onSelectChat={() => {}}
        onDeleteChat={handleDeleteChat}
        user={user}
        onLogout={() => { logout(); navigate("/login"); }}
      />

      <div className="flex-1 flex flex-col h-screen">
        {/* Top bar */}
        <div className="flex items-center justify-between border-b border-line px-4 py-3 bg-panel">
          <h2 className="font-display text-sm font-medium truncate max-w-md">
            {activeChat?.title || "New chat"}
          </h2>
          <div className="flex items-center gap-3">
            <div className="flex bg-panel2 border border-line rounded-sm p-0.5 text-xs font-mono">
              <button
                onClick={() => setMode("chat")}
                className={`px-2 py-1 rounded-sm ${mode === "chat" ? "bg-accent text-white" : "text-muted"}`}
              >
                Chat
              </button>
              <button
                onClick={() => setMode("image")}
                className={`px-2 py-1 rounded-sm ${mode === "image" ? "bg-accent text-white" : "text-muted"}`}
              >
                Generate image
              </button>
            </div>
            {mode === "chat" && (
              <ModelSelector models={chatModels} value={selectedModel} onChange={setSelectedModel} />
            )}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {messages.length === 0 && !streamingText && (
            <div className="h-full flex items-center justify-center text-center text-muted">
              <div>
                <p className="font-display text-lg mb-1">Start a conversation</p>
                <p className="text-sm">Pick a model above, or attach documents below to chat with RAG.</p>
              </div>
            </div>
          )}
          {messages.map((m) => (
            <MessageBubble key={m.id} role={m.role} content={m.content} imageUrl={m.image_url} />
          ))}
          {streamingText && <MessageBubble role="assistant" content={streamingText} streaming />}
          <div ref={bottomRef} />
        </div>

        {/* RAG panel */}
        {mode === "chat" && (
          <RagPanel chatId={activeChat?.id} useRag={!!activeChat?.use_rag} onToggleRag={handleToggleRag} />
        )}

        {/* Input */}
        <div className="border-t border-line p-4 bg-panel">
          <div className="flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              placeholder={mode === "image" ? "Describe the image you want..." : "Message..."}
              className="flex-1 resize-none bg-panel2 border border-line rounded-sm px-3 py-2 text-sm focus:border-accent outline-none max-h-32"
            />
            <button
              onClick={handleSend}
              disabled={sending || !input.trim()}
              className="bg-accent hover:bg-accent/90 disabled:opacity-50 text-white text-sm font-medium rounded-sm px-4 py-2 transition-colors"
            >
              {sending ? "..." : "Send"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
