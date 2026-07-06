'use client';

import BackButton from '../components/BackButton';

export default function TelemetryPage() {
  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-200 font-sans selection:bg-indigo-500/30 relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(99,102,241,0.08),transparent_45%)] pointer-events-none" />
      <main className="relative z-10 max-w-5xl mx-auto px-6 py-16">
        <BackButton />
        <div className="rounded-3xl bg-slate-900/60 border border-slate-800/70 backdrop-blur-xl p-8 shadow-2xl shadow-indigo-900/20">
          <h1 className="text-3xl font-extrabold text-white mb-3">Telemetry Ledgers</h1>
          <p className="text-slate-400 text-sm max-w-2xl mb-8 leading-relaxed">
            Historical evaluation metrics and system observability logs collected from your active Reposeer sessions.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl bg-slate-950/70 border border-slate-800 p-6">
              <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Latest Session</p>
              <p className="text-lg font-semibold text-white">No active telemetry loaded yet.</p>
            </div>
            <div className="rounded-2xl bg-slate-950/70 border border-slate-800 p-6">
              <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Performance Drift</p>
              <p className="text-lg font-semibold text-white">Awaiting your first workspace evaluation.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
