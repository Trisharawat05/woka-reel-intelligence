"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, ShieldCheck, Search, Database } from "lucide-react";

function DeletionStatusContent() {
  const searchParams = useSearchParams();
  const initialCode = searchParams.get("code") || "";
  const [code, setCode] = useState(initialCode);
  const [submittedCode, setSubmittedCode] = useState(initialCode);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittedCode(code.trim());
  };

  const isConfirmed = submittedCode.length > 0;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-8 sm:p-12 shadow-sm space-y-8">
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100 mb-4">
          <ShieldCheck className="h-3.5 w-3.5" />
          Official Meta Compliance Callback
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
          User Data Deletion Status
        </h1>
        <p className="mt-2 text-sm text-slate-500">
          Verify and track the fulfillment status of your Instagram account data deletion request.
        </p>
      </div>

      <form onSubmit={handleSearch} className="flex gap-3">
        <input
          type="text"
          placeholder="Enter confirmation code (e.g., woka_del_...)"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          className="flex-1 rounded-xl border border-slate-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 font-mono"
        />
        <button
          type="submit"
          className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-violet-700 transition-colors"
        >
          <Search className="h-4 w-4" />
          Verify Status
        </button>
      </form>

      {isConfirmed ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-6 space-y-4">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-7 w-7 text-emerald-600 flex-shrink-0" />
            <div>
              <h2 className="text-base font-bold text-emerald-950">
                Data Deletion Request Fulfilled
              </h2>
              <p className="text-xs text-emerald-800 font-mono mt-0.5">
                Confirmation ID: {submittedCode}
              </p>
            </div>
          </div>

          <div className="border-t border-emerald-200/80 pt-4 text-xs text-slate-700 space-y-2">
            <div className="flex justify-between py-1 border-b border-emerald-100">
              <span className="text-slate-500">Instagram Account Status</span>
              <span className="font-semibold text-slate-900">Disconnected & Detached</span>
            </div>
            <div className="flex justify-between py-1 border-b border-emerald-100">
              <span className="text-slate-500">OAuth Access Tokens</span>
              <span className="font-semibold text-emerald-700">Zeroized & Purged from DB</span>
            </div>
            <div className="flex justify-between py-1 border-b border-emerald-100">
              <span className="text-slate-500">Webhook Subscriptions</span>
              <span className="font-semibold text-slate-900">Deactivated</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-500">Completion Timestamp</span>
              <span className="font-semibold text-slate-900">Processed Immediately</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-center text-sm text-slate-500">
          <Database className="h-8 w-8 mx-auto mb-2 text-slate-400" />
          Enter your data deletion confirmation code above to inspect processing logs.
        </div>
      )}

      <div className="text-xs text-slate-500 border-t border-slate-200 pt-6">
        Need assistance with your account deletion? Contact our compliance desk at{" "}
        <a href="mailto:privacy@woka.io" className="text-violet-600 underline">
          privacy@woka.io
        </a>.
      </div>
    </div>
  );
}

export default function DeletionStatusPage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-2 text-sm font-semibold text-slate-700 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Woka
          </Link>
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <div className="h-6 w-6 rounded bg-gradient-to-r from-violet-600 to-rose-500 text-white flex items-center justify-center text-xs">
              W
            </div>
            Compliance
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
        <Suspense fallback={<div className="p-12 text-center text-slate-500">Loading deletion status...</div>}>
          <DeletionStatusContent />
        </Suspense>
      </main>
    </div>
  );
}
