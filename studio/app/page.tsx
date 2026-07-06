import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-200 font-sans selection:bg-indigo-500/30 relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(99,102,241,0.08),transparent_45%)] pointer-events-none" />

      <main className="max-w-5xl mx-auto px-6 pt-24 pb-16 relative z-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-xs font-medium text-indigo-400 mb-6 backdrop-blur-md">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
          v1.0 Local Sandbox Active
        </div>

        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-500 bg-clip-text text-transparent mb-4">
          Reposeer Studio.
        </h1>
        <p className="text-lg text-slate-400 max-w-2xl mb-10 leading-relaxed">
          An automated multi-agent engineering evaluation framework. Reposeer indexes your live codebase, runs static AST analysis, and hosts deep architectural technical drills to test production safety boundaries.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
          <div className="p-6 rounded-xl bg-slate-900/40 border border-slate-800/60 backdrop-blur-xl">
            <h3 className="text-sm font-semibold text-white mb-1">⚡ Deep AST Crawling</h3>
            <p className="text-xs text-slate-400">Extracts operational blueprints and vectorises code semantics automatically.</p>
          </div>
          <div className="p-6 rounded-xl bg-slate-900/40 border border-slate-800/60 backdrop-blur-xl">
            <h3 className="text-sm font-semibold text-white mb-1">🔬 Automated Grading</h3>
            <p className="text-xs text-slate-400">Asynchronous evaluator nodes log performance directly to your telemetry ledger.</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-4 items-center">
          <Link 
            href="/studio" 
            className="px-6 py-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-lg shadow-indigo-600/20 hover:shadow-indigo-600/30"
          >
            Launch Evaluation Workspace
          </Link>
          <Link 
            href="/telemetry" 
            className="px-6 py-3 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800/60 text-slate-300 font-medium text-sm transition-all"
          >
            View Telemetry Ledgers
          </Link>
        </div>
      </main>
    </div>
  );
}
