import React, { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, API_URL, expireSession } from "../api/client";
import { readChatStream } from "../api/stream";
import { describeError } from "../api/errors";
import Sidebar from "../components/Sidebar.jsx";
import ModelSelector from "../components/ModelSelector.jsx";
import MessageBubble from "../components/MessageBubble.jsx";
import RagPanel from "../components/RagPanel.jsx";
import MemoryPanel from "../components/MemoryPanel.jsx";

export default function Chat() {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const [chats, setChats] = useState([]);
  const [activeChat, setActiveChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [chatModels, setChatModels] = useState([]);
  const [imageModels, setImageModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [imageModel, setImageModel] = useState("nvidia::black-forest-labs/flux.2-klein-4b");
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [streamSources, setStreamSources] = useState([]);
  const [mode, setMode] = useState("chat");
  const [panel, setPanel] = useState(null);
  const [sidebar, setSidebar] = useState(false);
  const [useMemory, setUseMemory] = useState(() => localStorage.getItem("useMemory") !== "false");
  const [webSearch, setWebSearch] = useState(() => localStorage.getItem("webSearch") === "off" ? "off" : "auto");
  const [toolStatus, setToolStatus] = useState("");
  const [memoryRevision, setMemoryRevision] = useState(0);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [imageAttachment, setImageAttachment] = useState(null);
  const [contextInfo, setContextInfo] = useState(null);
  const bottomRef = useRef(null);
  const imageInputRef = useRef(null);
  const busy = useRef(false);
  const operation = useRef(0);
  const operationChat = useRef(null);
  const abort = useRef(null);
  const textarea = useRef(null);
  const currentModel = chatModels.find(m => m.id === selectedModel);
  const canSend = mode === "image" ? imageModels.some(m => m.id === imageModel && m.available) : currentModel?.available;

  async function refreshChats() { const { data } = await api.get("/chats"); setChats(data); }
  useEffect(() => {
    let live = true;
    Promise.all([api.get("/chats"), api.get("/models/chat"), api.get("/models/image")]).then(([c, m, i]) => {
      if (!live) return;
      setChats(c.data); setChatModels(m.data); setImageModels(i.data);
      setSelectedModel(previous => m.data.some(x => x.id === previous && x.available) ? previous : m.data.find(x => x.available)?.id || "");
    }).catch(err => { if (live) setError(describeError(err)); });
    return () => { live = false; abort.current?.abort(); };
  }, []);

  useEffect(() => {
    if (busy.current && operationChat.current === chatId) return;
    if (busy.current) { operation.current++; abort.current?.abort(); busy.current = false; setSending(false); setStreamingText(""); }
    let live = true;
    setError(""); setNotice(""); setImageAttachment(null); setContextInfo(null);
    if (!chatId) { setActiveChat(null); setMessages([]); setLoading(false); return; }
    setLoading(true); setMessages([]);
    Promise.all([api.get(`/chats/${chatId}`), api.get(`/chats/${chatId}/messages`)]).then(([c, m]) => {
      if (!live) return;
      setActiveChat(c.data); setMessages(m.data);
    }).catch(err => { if (live) { setActiveChat(null); setError(describeError(err)); } }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [chatId]);

  useEffect(() => {
    if (!activeChat || busy.current) return;
    const id = activeChat.default_model.includes("::") ? activeChat.default_model : `groq::${activeChat.default_model}`;
    if (chatModels.some(model => model.id === id && model.available)) setSelectedModel(id);
  }, [activeChat?.id, chatModels]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, streamingText]);
  useEffect(() => { if (textarea.current) { textarea.current.style.height = "auto"; textarea.current.style.height = `${Math.min(textarea.current.scrollHeight, 180)}px`; } }, [input]);

  async function ensureChat() {
    if (activeChat) return activeChat;
    const { data } = await api.post("/chats", { title: "New chat", default_model: selectedModel || "groq::openai/gpt-oss-20b" });
    operationChat.current = data.id; setActiveChat(data); setChats(c => [data, ...c]);
    navigate(`/chat/${data.id}`, { replace: true });
    return data;
  }
  async function newChat() {
    if (busy.current) return;
    navigate("/chat"); setInput(""); setSidebar(false); setPanel(null); setMessages([]); setActiveChat(null);
  }
  async function deleteChat(id) {
    try { await api.delete(`/chats/${id}`); setChats(c => c.filter(x => x.id !== id)); if (id === chatId) navigate("/chat"); }
    catch (err) { setError(describeError(err)); }
  }
  async function renameChat(chat) {
    const title = window.prompt("Conversation title", chat.title);
    if (!title?.trim()) return;
    try { const { data } = await api.patch(`/chats/${chat.id}`, { title: title.trim().slice(0, 120) }); setChats(c => c.map(x => x.id === data.id ? data : x)); if (chat.id === chatId) setActiveChat(data); }
    catch (err) { setError(describeError(err)); }
  }
  async function toggleRag(value) {
    try { const { data } = await api.patch(`/chats/${activeChat.id}`, { use_rag: value }); setActiveChat(previous => previous?.id === data.id ? data : previous); }
    catch (err) { setError(describeError(err)); }
  }
  async function openDocuments() {
    if (busy.current) return;
    try { await ensureChat(); setPanel(p => p === "documents" ? null : "documents"); }
    catch (err) { setError(describeError(err)); }
  }
  async function saveMemory(content) {
    try { await api.post("/memories", { content }); setMemoryRevision(r => r + 1); setNotice("Saved to memory."); }
    catch (err) { setError(describeError(err)); }
  }
  function attachImage(e) {
    const file = e.target.files?.[0]; e.target.value = "";
    if (!file) return;
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 2.5 * 1024 * 1024) { setError("Choose a PNG, JPEG or WebP image under 2.5 MB."); return; }
    const reader = new FileReader(); reader.onload = () => setImageAttachment({ url: reader.result, name: file.name }); reader.onerror = () => setError("Could not read image."); reader.readAsDataURL(file);
  }
  async function send() {
    if (busy.current || loading || !input.trim() || !canSend) return;
    busy.current = true; setSending(true); setError(""); setNotice(""); setStreamingText(""); setStreamSources([]); setContextInfo(null); setToolStatus("");
    const op = ++operation.current;
    operationChat.current = chatId || null;
    const text = input.trim(); const attachment = mode === "chat" ? imageAttachment : null;
    let chat;
    try {
      chat = await ensureChat();
      if (op !== operation.current) return;
      operationChat.current = chat.id;
      setInput(""); setImageAttachment(null);
      setMessages(m => [...m, { id: `local-${op}`, role: "user", content: text, image_url: attachment?.url }]);
      abort.current = new AbortController();
      if (mode === "image") {
        await api.post("/images/generate", { prompt: text, chat_id: chat.id, model: imageModel }, { signal: abort.current.signal });
      } else {
        const token = localStorage.getItem("token");
        const response = await fetch(`${API_URL}/chats/${chat.id}/messages`, {
          method: "POST", signal: abort.current.signal,
          headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
          body: JSON.stringify({ content: text, model: selectedModel, use_memory: useMemory, use_rag: chat.use_rag, web_search: webSearch, image_url: attachment?.url || null }),
        });
        if (response.status === 401) expireSession();
        if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`); }
        let fullText = "";
        await readChatStream(response, event => {
          if (op !== operation.current) return;
          if (event.meta) { setStreamSources(event.sources || []); setContextInfo(previous => ({ ...previous, ...event })); if (event.memory_saved) setMemoryRevision(r => r + 1); }
          if (event.status) setToolStatus(event.message || "Working...");
          if (event.warning) setNotice(previous => previous ? `${previous} ${event.warning}` : event.warning);
          if (event.delta) { fullText += event.delta; setStreamingText(fullText); }
        });
      }
    } catch (err) {
      if (op === operation.current) {
        if (err.name === "AbortError" || err.code === "ERR_CANCELED") setNotice("Generation stopped. You can send a new message.");
        else { setError(describeError(err)); setInput(text); }
      }
    } finally {
      if (op === operation.current) {
        if (chat) {
          try { const [c, m] = await Promise.all([api.get(`/chats/${chat.id}`), api.get(`/chats/${chat.id}/messages`)]); if (op === operation.current) { setActiveChat(c.data); setMessages(m.data); await refreshChats(); } }
          catch { setError(previous => previous || "Could not refresh saved history. Reload this conversation."); }
        }
        if (op === operation.current) { setStreamingText(""); setSending(false); busy.current = false; abort.current = null; }
      }
    }
  }

  return <div className="flex h-dvh bg-white text-text overflow-hidden">
    <Sidebar chats={chats} activeChatId={chatId} onNewChat={newChat} onDeleteChat={deleteChat} onRenameChat={renameChat} disabled={sending} open={sidebar} onClose={() => setSidebar(false)} />
    <main className="flex-1 min-w-0 flex flex-col">
      <header className="flex items-center justify-between gap-2 px-4 sm:px-7 py-3 border-b border-line/50 min-h-16">
        <div className="flex items-center gap-2 min-w-0"><button aria-label="Open sidebar" onClick={() => setSidebar(true)} className="md:hidden text-lg mr-1">☰</button><ModelSelector models={chatModels} value={selectedModel} onChange={value => { setSelectedModel(value); setImageAttachment(null); }} disabled={sending || loading || mode === "image"} /><span className="hidden lg:inline text-[10px] border border-line text-muted px-2 py-0.5 rounded-md">{currentModel?.provider || "Chat"}</span></div>
        <div className="flex items-center gap-1 sm:gap-2"><button onClick={openDocuments} disabled={sending || loading} className={`toolbar-button ${panel === "documents" ? "bg-panel2" : ""}`}>Documents{activeChat?.use_rag ? " ·" : ""}</button><button disabled={sending} onClick={() => setPanel(p => p === "memory" ? null : "memory")} className={`toolbar-button ${panel === "memory" ? "bg-panel2" : ""}`}>Memory</button></div>
      </header>
      <div className="flex flex-1 overflow-hidden relative">
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 overflow-y-auto px-4 sm:px-8" aria-live="polite" aria-busy={sending || loading}>
            <div className="max-w-3xl mx-auto py-8">
              {loading && <p className="text-center text-sm text-muted py-12">Loading conversation...</p>}
              {!loading && messages.length === 0 && !sending && <div className="empty-state">
                <div className="brand-mark large mb-7">a</div><p className="text-[11px] uppercase tracking-[0.2em] text-muted mb-3">A little clarity, on demand</p><h1 className="font-display text-3xl sm:text-4xl font-medium tracking-tight mb-4">Where should we begin?</h1><p className="text-sm text-muted max-w-md leading-6">Think something through, ask your documents, or turn an idea into an image.</p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full mt-10 text-left">
                  {[{ title: "Make it clearer", text: "Explain a complex idea", prompt: "Explain how large language models work using a simple analogy." }, { title: "Build something", text: "Get help with your code", prompt: "Help me plan a Python project. Ask me what I want to build." }, { title: "Imagine it", text: "Create an image with NVIDIA", prompt: "An architectural photograph of a quiet library surrounded by a misty forest, soft morning light.", image: true }].map(item => <button key={item.title} onClick={() => { setMode(item.image ? "image" : "chat"); setInput(item.prompt); textarea.current?.focus(); }} className="suggestion-card"><span className="block text-sm font-medium mb-2">{item.title} ↗</span><span className="text-xs text-muted leading-5">{item.text}</span></button>)}
                </div>
              </div>}
              {messages.map(m => <MessageBubble key={m.id} role={m.role} content={m.content} imageUrl={m.image_url} sources={m.sources} onRemember={sending ? undefined : saveMemory} />)}
              {sending && !streamingText && <div className="flex items-center gap-3 text-sm text-muted py-3"><span className="brand-mark small">a</span><span className="animate-pulse">{mode === "image" ? "Creating your image... This can take a minute." : toolStatus || "Thinking..."}</span></div>}
              {streamingText && <MessageBubble role="assistant" content={streamingText} sources={streamSources} streaming />}
              <div ref={bottomRef} />
            </div>
          </div>
          <div className="px-4 sm:px-8 pb-4 pt-2"><div className="max-w-3xl mx-auto">
            {error && <div role="alert" className="mb-3 rounded-xl bg-red-50 text-red-700 p-3 text-xs flex items-start gap-3"><span className="flex-1">{error}</span><button onClick={() => setError("")} aria-label="Dismiss error">×</button></div>}
            {notice && <p role="status" className="text-xs text-accent mb-3">{notice}</p>}
            <div className="rounded-3xl border border-line bg-white shadow-[0_4px_24px_rgba(0,0,0,0.04)] p-3 sm:p-4 focus-within:border-accent/50 transition-colors">
              {imageAttachment && <div className="flex items-center gap-2 text-xs mb-3"><img src={imageAttachment.url} alt="Attached preview" className="w-10 h-10 object-cover rounded-lg" /><span className="truncate">{imageAttachment.name}</span><button onClick={() => setImageAttachment(null)} aria-label="Remove attached image">×</button></div>}
              <textarea ref={textarea} aria-label={mode === "image" ? "Image description" : "Message"} value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(); } }} rows={2} maxLength={mode === "image" ? 2000 : 16000} placeholder={mode === "image" ? "Describe the image you have in mind..." : "Ask anything, or bring your own documents..."} className="w-full bg-transparent resize-none border-0 outline-none focus-visible:outline-none text-sm leading-6 min-h-14 max-h-44 px-1" />
              <div className="flex items-center justify-between gap-2 mt-2"><div className="flex items-center gap-1 sm:gap-2 flex-wrap">
                <button disabled={sending} onClick={() => { setMode("chat"); }} className={`mode-pill ${mode === "chat" ? "active" : ""}`}>Chat</button><button disabled={sending} onClick={() => { setMode("image"); setImageAttachment(null); }} className={`mode-pill ${mode === "image" ? "active" : ""}`}>Create image</button>
                {mode === "chat" && <button disabled={sending} aria-label="Automatic web search" aria-pressed={webSearch === "auto"} title="Let the assistant decide when to search Tavily. Toggle off to prevent web searches." onClick={() => { const next = webSearch === "auto" ? "off" : "auto"; setWebSearch(next); localStorage.setItem("webSearch", next); }} className={`mode-pill ${webSearch === "auto" ? "active" : ""}`}>Web: {webSearch === "auto" ? "Auto" : "Off"}</button>}
                {mode === "chat" && <button disabled={sending || !currentModel?.supports_vision} onClick={() => imageInputRef.current?.click()} title={currentModel?.supports_vision ? "Attach image" : "Select a vision model to attach images"} aria-label="Attach image" className="toolbar-button disabled:opacity-30">+ Image</button>}
                {mode === "image" && <select aria-label="Image model" value={imageModel} onChange={e => setImageModel(e.target.value)} disabled={sending} className="text-[11px] bg-transparent max-w-40"><option value="nvidia::black-forest-labs/flux.2-klein-4b">NVIDIA · FLUX.2</option></select>}
                <input ref={imageInputRef} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={attachImage} />
              </div>{sending ? <button aria-label="Stop generation" title="Stop generation" onClick={() => abort.current?.abort()} className="send-button"><span className="text-sm">■</span></button> : <button aria-label="Send message" title="Send message" onClick={send} disabled={!input.trim() || !canSend || loading} className="send-button">↑</button>}</div>
            </div>
            <p className="text-[10px] text-muted text-center mt-3">{mode === "image" ? "Images by NVIDIA NIM · Saved to this conversation" : `Auralis can make mistakes. Check important details. · Memory ${useMemory ? "on" : "off"}${activeChat?.use_rag ? " · Documents on" : ""}`}</p>
            {contextInfo && <p className="text-[10px] text-muted text-center mt-1">{contextInfo.history_messages} recent messages · {contextInfo.memory_count} saved memories · {contextInfo.sources.filter(source => source.kind !== "web").length} document passages · {contextInfo.sources.filter(source => source.kind === "web").length} web sources</p>}
          </div></div>
        </div>
        {panel && <aside className="absolute sm:static inset-y-0 right-0 w-[min(340px,100%)] shrink-0 bg-[#fafafb] border-l border-line p-5 overflow-y-auto shadow-lg sm:shadow-none z-10" aria-label={panel === "memory" ? "Memory panel" : "Documents panel"}><div className="flex justify-between items-center mb-6"><h2 className="font-display font-medium">{panel === "memory" ? "Your memory" : "Chat documents"}</h2><button onClick={() => setPanel(null)} aria-label="Close panel" className="text-muted text-xl">×</button></div>{panel === "memory" ? <MemoryPanel enabled={useMemory} onToggle={value => { setUseMemory(value); localStorage.setItem("useMemory", String(value)); }} revision={memoryRevision} disabled={sending} /> : <RagPanel key={activeChat?.id} chatId={activeChat?.id} useRag={activeChat?.use_rag || false} onToggleRag={toggleRag} disabled={sending} />}</aside>}
      </div>
    </main>
  </div>;
}
