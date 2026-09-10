import React, { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, API_URL } from "../api/client";
import Sidebar from "../components/Sidebar.jsx";
import ModelSelector from "../components/ModelSelector.jsx";
import MessageBubble from "../components/MessageBubble.jsx";
import RagPanel from "../components/RagPanel.jsx";

export default function Chat() {
  const { chatId } = useParams();
  const navigate = useNavigate();

  const [chats, setChats] = useState([]);
  const [activeChat, setActiveChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [chatModels, setChatModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("deepseek-v4-flash");
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [mode, setMode] = useState("chat"); // "chat" | "image"
  const bottomRef = useRef(null);

  // Load chat list + available models once.
  useEffect(() => {
    api.get("/chats")
      .then((r) => setChats(r.data))
      .catch((err) => console.error("Could not load chats:", err));

    api.get("/models/chat")
      .then((r) => {
        setChatModels(r.data);
        if (r.data.length && !selectedModel) {
          setSelectedModel(r.data[0].id);
        }
      })
      .catch((err) => console.error("Could not load models:", err));
  }, []);

  // Load the active chat + its messages whenever the route param changes.
  useEffect(() => {
    if (!chatId) {
      setActiveChat(null);
      setMessages([]);
      return;
    }
    api.get(`/chats/${chatId}`)
      .then((r) => {
        setActiveChat(r.data);
        if (r.data.default_model) {
          setSelectedModel(r.data.default_model);
        }
      })
      .catch((err) => console.error("Could not load chat details:", err));

    api.get(`/chats/${chatId}/messages`)
      .then((r) => setMessages(r.data))
      .catch((err) => console.error("Could not load messages:", err));
  }, [chatId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  const handleNewChat = useCallback(async () => {
    try {
      const { data } = await api.post("/chats", {
        title: "New chat",
        default_model: selectedModel || "deepseek-v4-flash",
      });
      setChats((c) => [data, ...c]);
      navigate(`/chat/${data.id}`);
    } catch (err) {
      console.error("Error creating new chat:", err);
    }
  }, [selectedModel, navigate]);

  const handleDeleteChat = useCallback(async (id) => {
    try {
      await api.delete(`/chats/${id}`);
      setChats((c) => c.filter((x) => x.id !== id));
      if (id === chatId) navigate("/chat");
    } catch (err) {
      console.error("Error deleting chat:", err);
    }
  }, [chatId, navigate]);

  const handleToggleRag = useCallback(async (value) => {
    if (!activeChat) return;
    try {
      await api.patch(`/chats/${activeChat.id}`, { use_rag: value });
      setActiveChat((c) => ({ ...c, use_rag: value }));
    } catch (err) {
      console.error("Error toggling RAG:", err);
    }
  }, [activeChat]);

  async function handleGenerateImage() {
    if (!input.trim()) return;
    const prompt = input;
    setInput("");
    setMessages((m) => [
      ...m,
      { id: `local-${Date.now()}`, role: "user", content: prompt, created_at: new Date().toISOString() },
    ]);
    setSending(true);
    try {
      const { data } = await api.post("/images/generate", { prompt });
      setMessages((m) => [
        ...m,
        {
          id: `img-${Date.now()}`,
          role: "assistant",
          content: `Generated image for: *${prompt}*`,
          image_url: data.url,
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: `Error generating image: ${err?.message || "Failed"}`,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  async function handleSend() {
    if (mode === "image") return handleGenerateImage();
    if (!input.trim()) return;

    let chat = activeChat;
    if (!chat) {
      try {
        const { data } = await api.post("/chats", {
          title: "New chat",
          default_model: selectedModel || "deepseek-v4-flash",
        });
        chat = data;
        setChats((c) => [data, ...c]);
        setActiveChat(data);
        navigate(`/chat/${data.id}`, { replace: true });
      } catch (err) {
        console.error("Could not auto-create chat:", err);
        return;
      }
    }

    const userText = input;
    setInput("");
    setMessages((m) => [
      ...m,
      { id: `local-${Date.now()}`, role: "user", content: userText, created_at: new Date().toISOString() },
    ]);
    setSending(true);
    setStreamingText("");

    try {
      const token = localStorage.getItem("token");
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const resp = await fetch(`${API_URL}/chats/${chat.id}/messages`, {
        method: "POST",
        headers,
        body: JSON.stringify({ content: userText, model: selectedModel || "deepseek-v4-flash" }),
      });

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server error ${resp.status}`);
      }

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
            setMessages((m) => [
              ...m,
              {
                id: payload.message_id || `msg-${Date.now()}`,
                role: "assistant",
                content: fullText,
                created_at: new Date().toISOString(),
              },
            ]);
            setStreamingText("");
          }
        }
      }
      setChats((cs) => cs.map((c) => (c.id === chat.id ? { ...c, title: userText.slice(0, 60) } : c)));
    } catch (err) {
      setStreamingText(`**Error:** ${err.message || "Failed to communicate with model"}`);
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
      />

      <div className="flex-1 flex flex-col h-screen">
        {/* Top bar */}
        <div className="flex items-center justify-between border-b border-line px-4 py-3 bg-panel">
          <h2 className="font-display text-sm font-medium truncate max-w-md">
            {activeChat?.title || "New Chat"}
          </h2>
          <div className="flex items-center gap-3">
            <div className="flex bg-panel2 border border-line rounded p-0.5 text-xs font-mono">
              <button
                onClick={() => setMode("chat")}
                className={`px-3 py-1 rounded transition-colors ${mode === "chat" ? "bg-accent text-white" : "text-muted hover:text-text"}`}
              >
                Chat
              </button>
              <button
                onClick={() => setMode("image")}
                className={`px-3 py-1 rounded transition-colors ${mode === "image" ? "bg-accent text-white" : "text-muted hover:text-text"}`}
              >
                Generate Image
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
              <div className="max-w-md p-6 rounded-xl bg-panel border border-line/60">
                <div className="text-3xl mb-3">⚡</div>
                <p className="font-display text-lg font-semibold text-text mb-1">Start a Conversation</p>
                <p className="text-sm text-muted mb-4">
                  Select an <span className="text-accent font-medium">AgentRouter</span> model (DeepSeek V4, GLM 5.3, Sol, Claude) or <span className="text-emerald-400 font-medium">Groq</span> model from the dropdown above.
                </p>
                <div className="flex flex-wrap gap-2 justify-center">
                  <button
                    onClick={() => { setInput("Tell me 3 interesting facts about quantum computing."); }}
                    className="text-xs bg-panel2 border border-line hover:border-accent px-3 py-1.5 rounded text-text transition-colors"
                  >
                    💡 Quantum facts
                  </button>
                  <button
                    onClick={() => { setInput("Write a concise Python script to scrape a webpage."); }}
                    className="text-xs bg-panel2 border border-line hover:border-accent px-3 py-1.5 rounded text-text transition-colors"
                  >
                    🐍 Python scraper
                  </button>
                </div>
              </div>
            </div>
          )}
          {messages.map((m) => (
            <MessageBubble key={m.id} role={m.role} content={m.content} imageUrl={m.image_url} />
          ))}
          {sending && !streamingText && (
            <div className="flex items-start gap-3 mb-4">
              <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center flex-shrink-0">
                <span className="text-sm">🤖</span>
              </div>
              <div className="flex-1 bg-panel2 border border-line rounded-lg px-4 py-3">
                <div className="flex items-center gap-2 text-muted text-sm">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-accent rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
                    <span className="w-2 h-2 bg-accent rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
                    <span className="w-2 h-2 bg-accent rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
                  </div>
                  <span>AI is working on your query...</span>
                </div>
              </div>
            </div>
          )}
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
              placeholder={mode === "image" ? "Describe the image you want to generate..." : "Message (AgentRouter & Groq connected)..."}
              className="flex-1 resize-none bg-panel2 border border-line rounded px-3 py-2 text-sm focus:border-accent outline-none max-h-32"
            />
            <button
              onClick={handleSend}
              disabled={sending || !input.trim()}
              className="bg-accent hover:bg-accent/90 disabled:opacity-50 text-white text-sm font-medium rounded px-5 py-2 transition-colors shadow-sm shadow-accent/20"
            >
              {sending ? "..." : "Send"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
