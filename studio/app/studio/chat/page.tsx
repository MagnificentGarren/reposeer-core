'use client';

import React, { useState, useEffect } from 'react';
import BackButton from '../../components/BackButton';

const getOrCreateSessionId = (): string => {
  if (typeof window === 'undefined') return 'ssr_default';

  let existingSession = localStorage.getItem('active_reposeer_session');
  if (!existingSession) {
    existingSession = `reposeer-session-${Date.now()}`;
    localStorage.setItem('active_reposeer_session', existingSession);
  }

  return existingSession;
};

export default function StudioChat() {
  const [sessionId, setSessionId] = useState<string>(() => getOrCreateSessionId());
  const [messages, setMessages] = useState<any[]>(() => {
    if (typeof window !== 'undefined') {
      const savedLogs = localStorage.getItem('reposeer_chat_history');
      if (savedLogs) {
        const parsed = JSON.parse(savedLogs);
        if (parsed.length > 0) return parsed;
      }
    }

    return [
      {
        role: 'assistant',
        content: 'Welcome back to the Reposeer evaluation terminal.'
      }
    ];
  });
  const [inputMessage, setInputMessage] = useState('');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('reposeer_chat_history', JSON.stringify(messages));
    }
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || sending) return;
    setSending(true);

    const userText = inputMessage;
    setInputMessage('');
    setMessages(prev => [...prev, { sender: 'user', text: userText }]);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText, session_id: sessionId })
      });
      const data = await response.json();
      if (data.reply) {
        setMessages(prev => [...prev, { sender: 'assistant', text: data.reply }]);
      }
    } catch (err) {
      console.error('Chat submit error:', err);
      setMessages(prev => [...prev, { sender: 'assistant', text: 'Unable to connect to chat backend.' }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-200 font-sans selection:bg-indigo-500/30 relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(99,102,241,0.08),transparent_45%)] pointer-events-none" />
      <main className="relative z-10 max-w-6xl mx-auto px-6 py-16">
        <BackButton />
        <div className="rounded-3xl bg-slate-900/60 border border-slate-800/70 backdrop-blur-xl p-8 shadow-2xl shadow-indigo-900/20">
          <h1 className="text-3xl font-extrabold text-white mb-3">Evaluation Chat Exam</h1>
          <p className="text-slate-400 text-sm max-w-2xl mb-8 leading-relaxed">
            Continue your active session and answer the evaluation prompts from the Reposeer agent.
          </p>
          <div className="grid gap-4">
            <div className="rounded-2xl bg-zinc-950/70 border border-zinc-800 p-6 space-y-4">
              {messages.map((message, idx) => (
                <div key={idx} className={`rounded-2xl p-4 ${message.sender === 'user' ? 'bg-indigo-500/10 self-end text-slate-100' : 'bg-slate-800/70 text-slate-300'}`}>
                  <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">{message.sender}</p>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.text || message.content}</p>
                </div>
              ))}
            </div>
            <form onSubmit={handleSendMessage} className="flex gap-3 mt-4">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Type your response..."
                className="flex-1 rounded-2xl border border-slate-800 bg-slate-950/80 px-4 py-3 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500/80"
              />
              <button
                type="submit"
                disabled={sending || !inputMessage.trim()}
                className="rounded-2xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-500 transition-all disabled:opacity-60"
              >
                Send
              </button>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}
