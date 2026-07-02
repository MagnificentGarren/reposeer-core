'use client';

import React, { useState, useEffect } from 'react';

interface BentoCardProps {
  label: string;
  title: string;
  children: React.ReactNode;
  className?: string;
}

const MetricBentoCard: React.FC<BentoCardProps> = ({ label, title, children, className = "" }) => {
  return (
    <div className={`bg-zinc-950/80 border border-zinc-800/60 rounded-lg p-5 backdrop-blur-md flex flex-col justify-between transition-all hover:border-zinc-700/50 ${className}`}>
      <div>
        <span className="text-[10px] font-mono tracking-widest text-zinc-500 uppercase block mb-1">
          {label}/
        </span>
        <h3 className="text-sm font-semibold text-zinc-200 tracking-tight mb-4">
          {title}
        </h3>
      </div>
      <div className="flex-1 flex flex-col justify-center">
        {children}
      </div>
    </div>
  );
};

export default function ReposeerDashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  
  // New chat interaction state hooks
  const [chatActive, setChatActive] = useState(false);
  const [messages, setMessages] = useState<Array<{ sender: 'user' | 'agent', text: string }>>([
    { sender: 'agent', text: 'System diagnostics complete. Ready to initialize multi-agent engineering mock framework.' }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/telemetry')
      .then((res) => res.json())
      .then((payload) => {
        setData(payload);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching telemetry: ", err);
        setLoading(false);
      });
  }, []);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || sending) return;

    const userText = inputMessage;
    setMessages(prev => [...prev, { sender: 'user', text: userText }]);
    setInputMessage('');
    setSending(true);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: userText,
          // Pass the message history length dynamically so the backend can accurately calculate the graph state
          session_id: String(messages.length)
        })
      });
      const resData = await response.json();
      
      if (resData.reply) {
        setMessages(prev => [...prev, { sender: 'agent', text: resData.reply }]);
      }
    } catch (err) {
      console.error("Failed to route message through agent pipelines:", err);
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center font-mono text-zinc-500 text-xs">
        <span>SYNCHRONIZING TELEMETRY PLATFORM CHANNELS...</span>
      </div>
    );
  }

  const metrics = data?.metrics || { Architecture: 0, "Backend Logic": 0, Security: 0, Databases: 0, Scalability: 0 };
  const weaknesses = data?.weaknesses || [];
  const modules = data?.blueprint?.modules || {};

  const pillarConfig = [
    { title: "System Structure & Topology", score: metrics["Architecture"], color: "bg-blue-500" },
    { title: "Defensive Security & Bounds", score: metrics["Security"], color: "bg-emerald-500" },
    { title: "Big-O Performance Optimization", score: metrics["Scalability"], color: "bg-purple-500" },
    { title: "Syntax Execution Mechanics", score: metrics["Backend Logic"], color: "bg-amber-500" },
    { title: "Data Flow & Index Architecture", score: metrics["Databases"], color: "bg-rose-500" },
  ];

  return (
    <div className="min-h-screen bg-black bg-gradient-to-b from-zinc-950 via-black to-black text-white">
      <header className="border-b border-zinc-900 bg-zinc-950/50 backdrop-blur-md sticky top-0 z-50 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]" />
          <span className="font-mono text-xs tracking-wider font-bold uppercase text-zinc-200">
            Reposeer // Studio Client
          </span>
        </div>
        <button 
          onClick={() => setChatActive(!chatActive)}
          className="text-xs bg-zinc-100 hover:bg-zinc-200 font-medium text-black px-3.5 py-1.5 rounded transition-colors"
        >
          {chatActive ? "View Metrics Matrix" : "Initialize Mock Exam"}
        </button>
      </header>

      <main className="max-w-7xl mx-auto p-6 lg:p-8 space-y-6">
        {!chatActive ? (
          <>
            {/* Standard Bento Configuration View */}
            <div className="space-y-1">
              <h1 className="text-xl font-bold tracking-tight text-zinc-100">Engineering Workspace Profile</h1>
              <p className="text-xs text-zinc-500 font-mono">Telemetry feed connected directly to local SQLite session registers.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <MetricBentoCard label="performance" title="Core Engineering Competency Mapping" className="md:col-span-2 lg:col-span-2 row-span-2">
                <div className="space-y-4 py-2">
                  {pillarConfig.map((pillar) => (
                    <div key={pillar.title} className="space-y-1.5">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-medium text-zinc-300">{pillar.title}</span>
                        <span className="font-mono text-zinc-400 font-semibold">{pillar.score}%</span>
                      </div>
                      <div className="w-full bg-zinc-900 rounded-full h-1 border border-zinc-800/40 overflow-hidden">
                        <div className={`h-full rounded-full ${pillar.color} transition-all duration-500`} style={{ width: `${pillar.score}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </MetricBentoCard>

              <MetricBentoCard label="memory_ledger" title="Identified Skill-Gap Focus Areas" className="col-span-1">
                <div className="flex flex-wrap gap-2 py-1">
                  {weaknesses.length > 0 ? (
                    weaknesses.map((tag: string) => (
                      <span key={tag} className="text-[11px] font-mono border border-zinc-800 bg-zinc-900/40 text-zinc-400 px-2.5 py-1 rounded">⚠️ {tag}</span>
                    ))
                  ) : (
                    <span className="text-xs font-mono text-zinc-600 italic py-2">No historical weaknesses synced yet. Perform an exam session loop to stream tags.</span>
                  )}
                </div>
              </MetricBentoCard>

              <MetricBentoCard label="repository_topology" title="Active Project Blueprint Explorer" className="md:col-span-1 lg:col-span-1">
                <div className="space-y-2 font-mono text-xs text-zinc-400 py-1 max-h-[220px] overflow-y-auto pr-1">
                  {Object.keys(modules).map((modKey) => {
                    const item = modules[modKey];
                    return (
                      <div key={modKey} className="p-2 rounded bg-zinc-900/30 border border-zinc-900/60 flex items-center justify-between">
                        <span className="truncate mr-2 text-zinc-300">📄 {modKey}</span>
                        <span className="text-[9px] bg-zinc-900 px-1.5 py-0.5 rounded text-blue-400 uppercase font-bold border border-zinc-800">{item.language || "code"}</span>
                      </div>
                    );
                  })}
                </div>
              </MetricBentoCard>
            </div>
          </>
        ) : (
          /* Live Focused Chat Environment (Adopting Clean Card Logic from Design 2) */
          <div className="space-y-4 max-w-4xl mx-auto">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold tracking-tight text-zinc-100">Active Examination Panel</h1>
                <p className="text-xs text-zinc-500 font-mono">Session loop processing actively via LangGraph orchestration node tree.</p>
              </div>
              <span className="text-[10px] uppercase font-mono tracking-widest px-2.5 py-1 rounded bg-blue-950/40 text-blue-400 border border-blue-900/40 animate-pulse">
                Live Session Trace
              </span>
            </div>

            <div className="bg-zinc-950 border border-zinc-900 rounded-xl min-h-[450px] flex flex-col justify-between overflow-hidden">
              {/* Output stream container */}
              <div className="p-6 space-y-4 flex-1 max-h-[400px] overflow-y-auto">
                {messages.map((msg, index) => (
                  <div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] rounded-lg px-4 py-2.5 text-xs font-sans leading-relaxed ${
                      msg.sender === 'user' 
                        ? 'bg-zinc-100 text-black font-medium' 
                        : 'bg-zinc-900 text-zinc-200 border border-zinc-800'
                    }`}>
                      {msg.text}
                    </div>
                  </div>
                ))}
                {sending && (
                  <div className="flex justify-start">
                    <div className="bg-zinc-900 text-zinc-500 border border-zinc-800 text-[10px] font-mono px-4 py-2 rounded-lg animate-pulse">
                      Orchestrator node compiling review evaluation...
                    </div>
                  </div>
                )}
              </div>

              {/* Input Form action zone */}
              <form onSubmit={handleSendMessage} className="border-t border-zinc-900 p-4 bg-zinc-950 flex items-center space-x-3">
                <input 
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder="Formulate engineering conceptual answer or solution state..."
                  className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2.5 text-xs text-zinc-200 focus:outline-none focus:border-zinc-700 font-sans transition-colors"
                  disabled={sending}
                />
                <button 
                  type="submit"
                  className="bg-zinc-100 hover:bg-zinc-200 text-black text-xs font-semibold px-4 py-2.5 rounded-lg transition-all shadow-md shrink-0 disabled:opacity-50"
                  disabled={sending}
                >
                  Stream Response
                </button>
              </form>
            </div>

            {/* Simulated Micro-Pill Controls Matching Design 2 Component Logic */}
            <div className="flex flex-wrap gap-2 pt-2 justify-center">
              <span className="text-[10px] font-mono border border-zinc-900 text-zinc-500 px-3 py-1 rounded-full uppercase">Esc: Abort Exam</span>
              <span className="text-[10px] font-mono border border-zinc-900 text-zinc-500 px-3 py-1 rounded-full uppercase">F5: Force Database Sync</span>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}