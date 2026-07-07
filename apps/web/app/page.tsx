"use client";

import { useEffect, useState } from "react";

interface Document {
  id: string;
  filename: string;
  status: string;
  createdAt: string;
}

export default function HomePage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/documents")
      .then((res) => res.json())
      .then((data) => setDocuments(data.documents ?? []))
      .catch(() => setDocuments([]))
      .finally(() => setLoading(false));
  }, []);

  const statusColor: Record<string, string> = {
    COMPLETED: "bg-success/20 text-success",
    PROCESSING: "bg-warning/20 text-warning",
    PENDING: "bg-white/10 text-white/60",
    FAILED: "bg-danger/20 text-danger",
  };

  return (
    <div className="animate-fade-in space-y-10">
      {/* ── Hero ──────────────────────────────────── */}
      <section className="flex flex-col items-center text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-accent/20 bg-accent/10 px-4 py-1.5 text-sm text-accent-light">
          <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
          Open-Source RAG Pipeline
        </div>
        <h1 className="font-display text-5xl font-extrabold leading-tight tracking-tight md:text-6xl">
          Intelligent Document
          <br />
          <span className="bg-gradient-to-r from-accent via-purple-400 to-pink-400 bg-clip-text text-transparent">
            Retrieval &amp; Chat
          </span>
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-white/50">
          Upload PDFs, CSVs, SQL files, text, code, and other readable files,
          then chat with your documents using LlamaIndex, pgvector, and
          open-source LLMs.
        </p>

        <div className="mt-8 flex gap-4">
          <a href="/upload" className="btn-primary">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
            Upload Document
          </a>
          <a href="/chat" className="btn-secondary">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
            </svg>
            Start Chat
          </a>
        </div>
      </section>

      {/* ── Document List ─────────────────────────── */}
      <section>
        <h2 className="font-display text-2xl font-bold mb-6">
          Your Documents
        </h2>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          </div>
        ) : documents.length === 0 ? (
          <div className="glass-card flex flex-col items-center py-16 text-center">
            <svg className="mb-4 h-12 w-12 text-white/20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12H9.75m3 0h3m-3-3h3m-6 3v.75m0-6.75h.008v.008H9.75V9zm0 3h.008v.008H9.75V12z" />
            </svg>
            <p className="text-white/40">No documents uploaded yet.</p>
            <a href="/upload" className="btn-primary mt-4 text-sm">
              Upload your first document
            </a>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {documents.map((doc) => (
              <div key={doc.id} className="glass-card-hover p-5 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10">
                      <svg className="h-5 w-5 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                      </svg>
                    </div>
                    <div>
                      <p className="font-medium text-white/90 truncate max-w-[180px]">
                        {doc.filename}
                      </p>
                      <p className="text-xs text-white/30">
                        {new Date(doc.createdAt).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`status-badge ${statusColor[doc.status] ?? statusColor.PENDING}`}
                  >
                    {doc.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
