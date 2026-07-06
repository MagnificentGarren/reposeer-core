'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import BackButton from '../components/BackButton';

const getOrCreateSessionId = (): string => {
  if (typeof window === "undefined") return "ssr_default";

  let existingSession = localStorage.getItem("active_reposeer_session");

  if (!existingSession) {
    existingSession = `reposeer-session-${Date.now()}`;
    localStorage.setItem("active_reposeer_session", existingSession);
  }

  return existingSession;
};

export default function StudioDashboard() {
  const router = useRouter();
  const [messages, setMessages] = useState<any[]>(() => {
    if (typeof window !== "undefined") {
      const savedLogs = localStorage.getItem("reposeer_chat_history");
      if (savedLogs) {
        const parsed = JSON.parse(savedLogs);
        if (parsed.length > 0) return parsed;
      }
    }

    return [
      {
        role: "assistant",
        content: (
          "### 🤖 Reposeer Core // Engineering Evaluation Framework\n\n" +
          "Welcome to the multi-agent system simulation arena. I am your evaluation **Architect** persona, and I will be testing your deep technical capabilities across your repository code layers.\n\n" +
          "**How this simulation works:**\n" +
          "* We will go through a **5-question technical drill** probing independent versioning, graph synchronization, and vector caching mechanisms.\n" +
          "* Every response you submit will be graded asynchronously by an expert evaluator node and logged directly to your telemetry ledger.\n\n" +
          "⚡ *To initialize the sandbox and receive your first architectural problem statement, type **'Let's begin'** below or hit the **Initialize** trigger mechanism.*"
        )
      }
    ];
  });

  const [sessionId, setSessionId] = useState<string>(() => getOrCreateSessionId());
  const [repoPath, setRepoPath] = useState<string>("");
  const [previousRepoPath, setPreviousRepoPath] = useState<string>("");
  const [repoUsedBefore, setRepoUsedBefore] = useState<boolean>(false);
  const [isWorkspaceConfigured, setIsWorkspaceConfigured] = useState<boolean>(() => {
    if (typeof window !== "undefined") {
      return !!localStorage.getItem("active_reposeer_session");
    }
    return false;
  });
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [blueprintUrl, setBlueprintUrl] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [showBlueprint, setShowBlueprint] = useState<boolean>(false);
  const [blueprintJson, setBlueprintJson] = useState<string | null>(null);
  const [inputMessage, setInputMessage] = useState('');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("reposeer_chat_history", JSON.stringify(messages));
    }
  }, [messages]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedRepo = localStorage.getItem("active_reposeer_repo_path") ?? "";
      setPreviousRepoPath(storedRepo);
      setRepoPath(storedRepo);
      const savedLogs = localStorage.getItem("reposeer_chat_history");
      setRepoUsedBefore(!!storedRepo && !!savedLogs);
    }
  }, []);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/telemetry')
      .then((res) => res.json())
      .then(() => {
        setTimeout(() => {}, 0);
      })
      .catch((err) => {
        console.error("Error fetching telemetry: ", err);
      });
  }, []);

  const handleResetSession = () => {
    const newSession = `reposeer-session-${Date.now()}`;
    if (typeof window !== "undefined") {
      localStorage.removeItem("reposeer_chat_history");
      localStorage.removeItem("active_reposeer_repo_path");
      localStorage.setItem("active_reposeer_session", newSession);
    }
    setMessages([]);
    setRepoPath("");
    setPreviousRepoPath("");
    setRepoUsedBefore(false);
    setIsWorkspaceConfigured(false);
    setSessionId(newSession);
  };

  const handleConfigureWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoPath.trim()) return;
    setIsScanning(true);

    try {
      if (typeof window !== "undefined") {
        localStorage.setItem("active_reposeer_session", sessionId);
      }
      const response = await fetch("http://127.0.0.1:8000/api/repo/select", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_path: repoPath.trim(), session_id: sessionId })
      });
      const data = await response.json();
      if (data.status === "success") {
        setIsWorkspaceConfigured(true);
        localStorage.setItem("active_reposeer_repo_path", repoPath.trim());
        setPreviousRepoPath(repoPath.trim());
        setRepoUsedBefore(true);
        const url = `http://127.0.0.1:8000/api/blueprint/${sessionId}`;
        setBlueprintUrl(url);
        setToastMessage(`Workspace indexed — blueprint available.`);
        setMessages(prev => [
          ...prev,
          {
            role: "assistant",
            content: `### 📁 Workspace Target Mounted\n\nSuccessfully indexed codebase at \`${repoPath}\` (${data.file_count} files discovered).\n\nType **'Let's begin'** to initialize your custom evaluation loop.`
          }
        ]);
        router.push('/studio/chat');
      } else {
        alert(`Ingestion Error: ${data.detail || "Failed to scan folder"}`);
      }
    } catch (err) {
      console.error(err);
      alert("Connection to graph ingestion server failed.");
    } finally {
      setIsScanning(false);
    }
  };

  const handleRedoExam = async () => {
    if (!repoPath.trim()) return;
    setIsScanning(true);

    const newSession = `reposeer-session-${Date.now()}`;
    if (typeof window !== "undefined") {
      localStorage.removeItem("reposeer_chat_history");
      localStorage.setItem("active_reposeer_session", newSession);
      localStorage.setItem("active_reposeer_repo_path", repoPath.trim());
    }
    setMessages([]);
    setSessionId(newSession);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/repo/select", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_path: repoPath.trim(), session_id: newSession })
      });
      const data = await response.json();
      if (data.status === "success") {
        setIsWorkspaceConfigured(true);
        setBlueprintUrl(`http://127.0.0.1:8000/api/blueprint/${newSession}`);
        setToastMessage(`Redo started — new evaluation session created.`);
        router.push('/studio/chat');
      } else {
        alert(`Redo Error: ${data.detail || "Failed to re-index folder"}`);
      }
    } catch (err) {
      console.error(err);
      alert("Connection to graph ingestion server failed.");
    } finally {
      setIsScanning(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || sending) return;
    setSending(true);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: inputMessage, session_id: sessionId })
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

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-200 font-sans selection:bg-indigo-500/30 relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(99,102,241,0.08),transparent_45%)] pointer-events-none" />
      <main className="relative z-10 max-w-6xl mx-auto px-6 py-16">
        <BackButton />

        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <section className="rounded-3xl bg-slate-900/60 border border-slate-800/70 backdrop-blur-xl p-8 shadow-2xl shadow-indigo-900/20">
            <h1 className="text-3xl font-extrabold text-white mb-3">Studio Workspace</h1>
            <p className="text-slate-400 text-sm max-w-2xl mb-8 leading-relaxed">
              Use the workspace builder to mount your codebase and unlock the architectural evaluation engine.
            </p>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl bg-slate-950/70 border border-slate-800 p-6">
                <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Workspace Status</p>
                <p className="text-lg font-semibold text-white">{isWorkspaceConfigured ? 'Connected' : 'Disconnected'}</p>
              </div>
              <div className="rounded-2xl bg-slate-950/70 border border-slate-800 p-6">
                <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Session ID</p>
                <p className="text-lg font-semibold text-white">{sessionId}</p>
              </div>
            </div>
          </section>

          <section className="rounded-3xl bg-slate-900/70 border border-slate-800 p-8 backdrop-blur-xl">
            <h2 className="text-xl font-semibold text-white mb-4">Launch the evaluation flow</h2>
            <form onSubmit={handleConfigureWorkspace} className="space-y-4">
              <label className="block text-xs uppercase tracking-widest text-slate-500">Local Repository Path</label>
              <input
                type="text"
                value={repoPath}
                onChange={(e) => setRepoPath(e.target.value)}
                placeholder="C:\\Users\\User\\Documents\\VS projects\\AssetCitadel"
                className="w-full rounded-2xl border border-slate-800 bg-slate-950/80 px-4 py-3 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500/80"
              />
              <button
                type="submit"
                disabled={isScanning || !repoPath.trim()}
                className="w-full rounded-2xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/10 hover:bg-indigo-500 transition-all disabled:opacity-50"
              >
                {isScanning ? 'Indexing Workspace…' : 'Index Codebase & Run Handshake'}
              </button>
              {repoUsedBefore && repoPath.trim() && repoPath.trim() === previousRepoPath && (
                <button
                  type="button"
                  onClick={handleRedoExam}
                  disabled={isScanning}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-sm font-semibold text-slate-200 hover:bg-slate-800 transition-all disabled:opacity-50"
                >
                  {isScanning ? 'Preparing Redo…' : 'Redo Exam for This Repo'}
                </button>
              )}
            </form>
          </section>
        </div>
      </main>
    </div>
  );
}
