import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";

export const metadata: Metadata = {
  title: "Woka — Creator Growth, Instagram Automation & Brand Collaboration",
  description: "Automate Instagram Comment-to-DM, analyze growth velocity, pitch verified media kits, and collaborate with top brands from one unified workspace.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased selection:bg-violet-100 selection:text-violet-900">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
