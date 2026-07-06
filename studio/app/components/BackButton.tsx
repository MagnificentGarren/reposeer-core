'use strict';
'use client';

import { useRouter } from 'next/navigation';

export default function BackButton() {
  const router = useRouter();

  return (
    <button
      onClick={() => router.push('/')}
      className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-white rounded-md bg-slate-900/60 border border-slate-800/80 backdrop-blur-md transition-all hover:border-slate-700/80 mb-6 group"
    >
      <svg
        className="w-3.5 h-3.5 transform transition-transform group-hover:-translate-x-0.5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
      </svg>
      Back to Dashboard
    </button>
  );
}
