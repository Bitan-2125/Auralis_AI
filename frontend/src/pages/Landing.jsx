import React from "react";
import { useNavigate } from "react-router-dom";

const features = [
  {
    icon: "⚡",
    title: "AgentRouter & Groq",
    desc: "Seamlessly powered by AgentRouter for frontier models and Groq for blazing millisecond inference.",
  },
  {
    icon: "🧠",
    title: "Frontier Models",
    desc: "Switch between DeepSeek V4 Flash, GLM 5.3, GPT 5.6 Sol, Claude Opus 4.8 & 5, and LLaMA.",
  },
  {
    icon: "🔓",
    title: "Instant Access",
    desc: "Sign up in seconds with just your email and password. Your chats and documents are saved to your account.",
  },
  {
    icon: "📄",
    title: "Document RAG",
    desc: "Upload PDFs, Word documents, and extract contextual intelligence directly into your conversation.",
  },
  {
    icon: "🎨",
    title: "Image Generation",
    desc: "Generate high-fidelity AI imagery in real-time alongside your chat stream.",
  },
  {
    icon: "💬",
    title: "Session Persistence",
    desc: "All your chat histories, models, and documents organized seamlessly in the sidebar.",
  },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-ink text-text font-body overflow-x-hidden">
      {/* Navbar */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-line bg-panel/80 backdrop-blur sticky top-0 z-50">
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate("/chat")}>
          <span className="w-2.5 h-2.5 rounded-full bg-signal animate-pulse"></span>
          <span className="font-mono text-xs tracking-widest text-text font-bold uppercase">Auralis AI</span>
          <span className="text-[10px] font-mono px-2 py-0.5 bg-accent/20 text-accent border border-accent/40 rounded ml-2">
            AgentRouter Active
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/login")}
            className="text-sm bg-accent hover:bg-accent/90 text-white font-medium px-5 py-2 rounded transition-colors shadow-sm shadow-accent/20"
          >
            Start Chatting →
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative flex flex-col items-center justify-center text-center px-6 pt-24 pb-20">
        {/* Background glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[650px] h-[450px] bg-accent/15 rounded-full blur-3xl pointer-events-none" />

        <div className="inline-flex items-center gap-2 bg-panel border border-line rounded-full px-4 py-1.5 text-xs text-muted font-mono mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-signal"></span>
          AgentRouter & Groq · Multi-Model Intelligence
        </div>

        <h1 className="font-display text-5xl md:text-7xl font-bold text-text leading-tight max-w-4xl mb-6">
          Frontier AI Intelligence with{" "}
          <span className="text-accent">Auralis</span>
        </h1>

        <p className="text-muted text-lg md:text-xl max-w-2xl mb-10 leading-relaxed">
          Access next-gen reasoning models including <strong className="text-text">DeepSeek V4 Flash</strong>, <strong className="text-text">GLM 5.3</strong>, <strong className="text-text">Claude Opus</strong>, and <strong className="text-text">Groq</strong> in one unified interface.
        </p>

        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate("/login")}
            className="bg-accent hover:bg-accent/90 text-white font-semibold text-base px-8 py-3 rounded-lg transition-all shadow-lg shadow-accent/25 hover:shadow-accent/45 hover:scale-[1.02]"
          >
            Use it for free →
          </button>
        </div>

        {/* Hero preview card */}
        <div className="mt-14 w-full max-w-2xl bg-panel border border-line rounded-xl shadow-2xl overflow-hidden text-left">
          <div className="flex items-center justify-between px-4 py-3 border-b border-line bg-panel2">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-400/70"></span>
              <span className="w-3 h-3 rounded-full bg-yellow-400/70"></span>
              <span className="w-3 h-3 rounded-full bg-green-400/70"></span>
              <span className="ml-3 text-xs text-muted font-mono">agentrouter · deepseek-v4-flash</span>
            </div>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/60">
              Live Streaming
            </span>
          </div>
          <div className="p-5 space-y-4 text-sm">
            <div className="flex justify-end">
              <div className="bg-accent text-white px-4 py-2.5 rounded-lg rounded-br-sm max-w-xs">
                How does quantum teleportation work?
              </div>
            </div>
            <div className="flex justify-start">
              <div className="bg-panel2 border border-line text-text px-4 py-2.5 rounded-lg rounded-bl-sm max-w-md leading-relaxed">
                Quantum teleportation transfers quantum information between two entangled particles without physically transmitting the particle itself. It relies on shared entanglement and classical communication.
                <span className="inline-block w-1.5 h-4 bg-accent ml-1 animate-pulse align-middle rounded-sm"></span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 py-20 max-w-5xl mx-auto">
        <h2 className="font-display text-3xl font-bold text-center mb-2">Capabilities & Models</h2>
        <p className="text-muted text-center mb-12">Built for speed, accuracy, and versatility.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((f) => (
            <div
              key={f.title}
              className="bg-panel border border-line rounded-xl p-5 hover:border-accent/50 hover:shadow-lg hover:shadow-accent/5 transition-all"
            >
              <div className="text-2xl mb-3">{f.icon}</div>
              <h3 className="font-display font-semibold text-text mb-1">{f.title}</h3>
              <p className="text-sm text-muted leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-20 text-center">
        <div className="max-w-xl mx-auto bg-panel border border-line rounded-2xl p-10 shadow-xl relative overflow-hidden">
          <div className="absolute inset-0 bg-accent/5 pointer-events-none" />
          <h2 className="font-display text-3xl font-bold mb-3">Ready to chat?</h2>
          <p className="text-muted mb-8">Sign in or create a free account to get started.</p>
          <button
            onClick={() => navigate("/login")}
            className="bg-accent hover:bg-accent/90 text-white font-semibold px-10 py-3 rounded-lg transition-all shadow-lg shadow-accent/20 text-base"
          >
            Use it for free →
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-line px-8 py-6 flex items-center justify-between text-xs text-muted">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-signal"></span>
          <span className="font-mono tracking-widest uppercase">Auralis AI</span>
        </div>
        <span>Powered by AgentRouter & Groq</span>
      </footer>
    </div>
  );
}
