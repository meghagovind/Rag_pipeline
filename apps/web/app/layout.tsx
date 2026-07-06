import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DocRAG — Intelligent Document Retrieval",
  description:
    "Upload documents and ask questions. Powered by open-source AI with LlamaIndex, pgvector, and Ollama.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-surface text-white antialiased">
        {/* ── Navigation ─────────────────────────── */}
        <nav className="sticky top-0 z-50 border-b border-white/[0.06] bg-surface/80 backdrop-blur-lg">
          <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
            <a href="/" className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/20">
                <svg
                  className="h-5 w-5 text-accent"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                  />
                </svg>
              </div>
              <span className="font-display text-xl font-bold tracking-tight">
                Doc<span className="text-accent">RAG</span>
              </span>
            </a>

            <div className="flex items-center gap-2">
              <a href="/upload" className="btn-secondary text-sm">
                Upload
              </a>
              <a href="/chat" className="btn-primary text-sm">
                Chat
              </a>
            </div>
          </div>
        </nav>

        {/* ── Main content ───────────────────────── */}
        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
