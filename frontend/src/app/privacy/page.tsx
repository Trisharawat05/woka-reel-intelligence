import Link from "next/link";
import { ArrowLeft, ShieldCheck, Lock, Trash2, Eye } from "lucide-react";

export const metadata = {
  title: "Privacy Policy — Woka",
  description: "Woka Privacy Policy and Data Handling Practices for Instagram Creators and Brands.",
};

export default function PrivacyPolicyPage() {
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
              <ShieldCheck className="h-3.5 w-3.5" />
              Effective Date: October 16, 2026
            </div>
            <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Privacy Policy</h1>
            <p className="mt-2 text-sm text-slate-500">
              How Woka collects, protects, uses, and deletes creator and end-user data in accordance with Meta Platform Terms.
            </p>
          </div>

          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Eye className="h-5 w-5 text-violet-600" />
              1. Information We Collect
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Woka operates as a creator engagement and automation platform. When you connect an Instagram Professional account to Woka, we request official permissions via Meta Graph API:
            </p>
            <ul className="list-disc list-inside text-sm text-slate-600 space-y-1 pl-2">
              <li><strong>Basic Profile Information:</strong> Instagram username, profile picture, user ID, and follower benchmarks via <code className="bg-slate-100 px-1 py-0.5 rounded text-xs">instagram_basic</code>.</li>
              <li><strong>Inbound Public Comments:</strong> Public comments left on your posts and reels via <code className="bg-slate-100 px-1 py-0.5 rounded text-xs">instagram_manage_comments</code> to match creator-defined trigger keywords.</li>
              <li><strong>Direct Message Dispatch:</strong> Messaging permissions via <code className="bg-slate-100 px-1 py-0.5 rounded text-xs">instagram_manage_messages</code> strictly to deliver the specific automated reply or resource requested by the commenter.</li>
              <li><strong>Connected Facebook Pages:</strong> Page discovery via <code className="bg-slate-100 px-1 py-0.5 rounded text-xs">pages_show_list</code> and engagement metrics via <code className="bg-slate-100 px-1 py-0.5 rounded text-xs">pages_read_engagement</code>.</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Lock className="h-5 w-5 text-violet-600" />
              2. Data Protection & Token Encryption
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              All Meta OAuth access tokens are encrypted at rest using AES-256 (Fernet symmetric encryption) before storage in our database. Plaintext tokens are never logged, displayed in client interfaces, or exposed in API responses. Session tokens utilize HMAC-SHA256 JWTs with 60-minute expiration windows and server-side revocation tracking.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Trash2 className="h-5 w-5 text-rose-500" />
              3. User Data Deletion Instructions (Meta Compliance)
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Woka complies strictly with Meta Platform Data Deletion requirements. Users can request total deletion of their connected data at any time through the following mechanisms:
            </p>
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-sm text-slate-700 space-y-2">
              <p><strong>Option A — In-App Disconnect:</strong> In your Woka Dashboard under <em>Instagram Settings</em>, click <strong>Disconnect Account</strong>. This immediately purges all stored tokens and detaches your profile.</p>
              <p><strong>Option B — Via Instagram Settings:</strong> Go to your Instagram Settings &rarr; Apps and Websites &rarr; Remove Woka. Meta will automatically dispatch a signed deauthorization and data deletion callback to our server.</p>
              <p><strong>Option C — Deletion Status Verification:</strong> You can track your data deletion confirmation code on our <Link href="/deletion-status" className="text-violet-600 font-semibold underline">Data Deletion Status Page</Link>.</p>
            </div>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900">4. Anti-Spam & Messaging Policies</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Woka enforces strict compliance with Instagram Direct Messaging policies:
            </p>
            <ul className="list-disc list-inside text-sm text-slate-600 space-y-1 pl-2">
              <li>Messages are only dispatched in direct response to user-initiated keyword comments.</li>
              <li>A mandatory recipient cooldown (minimum 60 minutes) prevents repeated messaging to the same Instagram account.</li>
              <li>Automated messages never contain deceptive links, unsolicited marketing, or unauthorized mass communications.</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900">5. Contact Information</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              For privacy inquiries, audit requests, or data deletion confirmations, contact our Data Protection Officer at: <a href="mailto:privacy@woka.io" className="text-violet-600 font-semibold underline">privacy@woka.io</a>.
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
