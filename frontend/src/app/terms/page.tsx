import Link from "next/link";
import { ArrowLeft, FileText, CheckCircle2, AlertTriangle } from "lucide-react";

export const metadata = {
  title: "Terms of Service — Woka",
  description: "Woka Terms of Service and Acceptable Use Policy.",
};

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-sm font-semibold text-slate-700 hover:text-slate-900 transition-colors">
            <ArrowLeft className="h-4 w-4" />
            Back to Woka
          </Link>
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <div className="h-6 w-6 rounded bg-gradient-to-r from-violet-600 to-rose-500 text-white flex items-center justify-center text-xs">
              W
            </div>
            Woka Legal
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
        <div className="bg-white rounded-2xl border border-slate-200 p-8 sm:p-12 shadow-sm space-y-8">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-violet-50 text-violet-700 border border-violet-100 mb-4">
              <FileText className="h-3.5 w-3.5" />
              Last Updated: October 16, 2026
            </div>
            <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Terms of Service</h1>
            <p className="mt-2 text-sm text-slate-500">
              Rules and acceptable use policies governing Woka accounts, automation tools, and marketplace collaborations.
            </p>
          </div>

          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              1. Platform Purpose & Eligibility
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Woka provides automation, growth insights, and campaign management software for verified Instagram creators, agencies, and brands. By creating an account or connecting an Instagram account, you warrant that you are authorized to manage that account and that your activities comply with Instagram Community Guidelines and Meta Platform Terms.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              2. Acceptable Use & Anti-Spam Obligations
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Creators using Woka comment-to-DM automations must strictly adhere to the following operational standards:
            </p>
            <ul className="list-disc list-inside text-sm text-slate-600 space-y-1.5 pl-2">
              <li><strong>Permission-Based Triggers:</strong> Automations must only be configured to respond to comments where the post explicitly invites comments (e.g., &quot;Comment GUIDE to receive the PDF&quot;).</li>
              <li><strong>Zero Prohibited Content:</strong> Messages must not promote illegal substances, hate speech, deceptive pyramid schemes, unsolicited financial advice, or copyright-infringing media.</li>
              <li><strong>Respect Anti-Spam Cooldowns:</strong> Users must not bypass, tamper with, or circumvent system rate limits or recipient cooldown timers.</li>
              <li><strong>No Scraping or Token Abuse:</strong> Attempting to access private endpoints, harvest third-party user data, or evade Meta Graph API rate limits is cause for immediate account termination.</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900">3. Brand Marketplace & Deliverable Commitments</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Campaign agreements executed through the Woka Brand Marketplace constitute binding contracts between the creator workspace and the brand workspace. Brands must honor agreed compensation upon approved deliverable verification, and creators must deliver creative assets by specified milestone deadlines.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900">4. Disclaimers & Limitation of Liability</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Woka is an independent SaaS platform utilizing official Meta Graph APIs. Woka is not endorsed, certified, or sponsored by Meta Platforms, Inc. We do not guarantee specific follower growth, engagement gains, or revenue numbers.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900">5. Termination & Data Purge</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Either party may terminate service at any time. Upon account closure or disconnection of your Instagram account, all stored OAuth credentials are permanently purged from Woka active databases within 24 hours.
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
