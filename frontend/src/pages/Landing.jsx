import React from "react";
import { useNavigate } from "react-router-dom";

const features = [
  {
    icon: "⚡",
    title: "Lightning Fast",
    desc: "Powered by Groq's LPU inference engine — responses in milliseconds, not seconds.",
  },
  {
    icon: "🧠",
    title: "Multiple Models",
    desc: "Switch between LLaMA, Mixtral, Gemma and more — all in one place.",
  },
  {
    icon: "📄",
    title: "RAG Support",
    desc: "Upload PDFs, Word docs, and let Auralis answer questions from your own documents.",
  },
  {
    icon: "🎨",
    title: "Image Generation",
    desc: "Generate stunning images from text prompts without leaving the chat.",
  },
  {
    icon: "💬",
    title: "Chat History",
    desc: "All your conversations saved and organized — pick up right where you left off.",
  },
  {
    icon: "🔒",
    title: "Private & Secure",
    desc: "Your data stays yours. Each account is isolated with JWT-based authentication.",
  },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-ink text-text font-body overflow-x-hidden">
      {/* Navbar */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-line bg-panel/80 backdrop-blur sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-signal animate-pulse"></span>
          <span className="font-mono text-xs tracking-widest text-muted uppercase">Auralis AI</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/login")}
            className="text-sm text-muted hover:text-text transition-colors px-4 py-1.5"
          >
            Sign in
          </button>
          <button
            onClick={() => navigate("/register")}
            className="text-sm bg-accent hover:bg-accent/90 text-white font-medium px-4 py-1.5 rounded-md transition-colors"
          >
            Get started
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative flex flex-col items-center justify-center text-center px-6 pt-28 pb-24">
        {/* Background glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-accent/10 rounded-full blur-3xl pointer-events-none" />

        <div className="inline-flex items-center gap-2 bg-panel border border-line rounded-full px-4 py-1.5 text-xs text-muted font-mono mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-signal"></span>
          Powered by Groq · Ultra-low latency AI
        </div>

        <h1 className="font-display text-5xl md:text-7xl font-bold text-text leading-tight max-w-3xl mb-6">
          Think faster with{" "}
          <span className="text-accent">Auralis AI</span>
        </h1>

        <p className="text-muted text-lg md:text-xl max-w-xl mb-10 leading-relaxed">
          A blazing-fast AI chat platform with multi-model support, document intelligence, and image generation — all in one clean interface.
        </p>

        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate("/register")}
            className="bg-accent hover:bg-accent/90 text-white font-semibold text-base px-8 py-3 rounded-lg transition-all shadow-lg shadow-accent/20 hover:shadow-accent/40"
          >
            Use it free →
          </button>
          <button
            onClick={() => navigate("/login")}
            className="text-sm text-muted hover:text-text border border-line px-6 py-3 rounded-lg transition-colors bg-panel"
          >
            Sign in
          </button>
        </div>

        {/* Hero preview card */}
        <div className="mt-16 w-full max-w-2xl bg-panel border border-line rounded-xl shadow-2xl overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-line bg-panel2">
            <span className="w-3 h-3 rounded-full bg-red-400/70"></span>
            <span className="w-3 h-3 rounded-full bg-yellow-400/70"></span>
            <span className="w-3 h-3 rounded-full bg-green-400/70"></span>
            <span className="ml-3 text-xs text-muted font-mono">auralis · llama-3.3-70b</span>
          </div>
          <div className="p-5 space-y-4 text-left text-sm">
            <div className="flex justify-end">
              <div className="bg-accent text-white px-4 py-2.5 rounded-lg rounded-br-sm max-w-xs">
                Explain quantum entanglement in simple terms
              </div>
            </div>
            <div className="flex justify-start">
              <div className="bg-panel2 border border-line text-text px-4 py-2.5 rounded-lg rounded-bl-sm max-w-sm leading-relaxed">
                Quantum entanglement is when two particles become linked — measuring one{" "}
                <span className="text-accent font-medium">instantly</span> affects the other,
                no matter the distance. Einstein called it{" "}
                <span className="italic text-muted">"spooky action at a distance."</span>
                <span className="inline-block w-1.5 h-4 bg-accent ml-1 animate-pulse align-middle rounded-sm"></span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 py-20 max-w-5xl mx-auto">
        <h2 className="font-display text-3xl font-bold text-center mb-2">Everything you need</h2>
        <p className="text-muted text-center mb-12">Built for speed, depth, and simplicity.</p>
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
      <section className="px-6 py-24 text-center">
        <div className="max-w-xl mx-auto bg-panel border border-line rounded-2xl p-10 shadow-xl relative overflow-hidden">
          <div className="absolute inset-0 bg-accent/5 pointer-events-none" />
          <h2 className="font-display text-3xl font-bold mb-3">Ready to get started?</h2>
          <p className="text-muted mb-8">Create a free account and start chatting in seconds.</p>
          <button
            onClick={() => navigate("/register")}
            className="bg-accent hover:bg-accent/90 text-white font-semibold px-10 py-3 rounded-lg transition-all shadow-lg shadow-accent/20 text-base"
          >
            Use Auralis AI →
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-line px-8 py-6 flex items-center justify-between text-xs text-muted">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-signal"></span>
          <span className="font-mono tracking-widest uppercase">Auralis AI</span>
        </div>
        <span>Built with Groq · FastAPI · React</span>
      </footer>
    </div>
  );
}
