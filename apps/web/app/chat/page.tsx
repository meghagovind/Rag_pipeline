"use client";

import { useEffect, useRef, useState } from "react";

interface Source {
  chunk_text: string;
  page_number: number;
  filename: string;
  score: number;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

interface Document {
  id: string;
  filename: string;
  status: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<string>("");
  const [expandedSource, setExpandedSource] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/documents")
      .then((r) => r.json())
      .then((d) =>
        setDocuments(
          (d.documents ?? []).filter(
            (doc: Document) => doc.status === "COMPLETED"
          )
        )
      )
      .catch(() => {});
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || loading) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          document_id: selectedDoc || undefined,
        }),
      });

      const data = await res.json();

      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.answer ?? "No answer received.",
        sources: data.sources ?? [],
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "Sorry, something went wrong. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="animate-fade-in flex h-[calc(100vh-7rem)] flex-col">
      {/* ── Header bar ───────────────────────────── */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
        <h1 className="font-display text-2xl font-bold">Chat with Documents</h1>
        <select
          value={selectedDoc}
          onChange={(e) => setSelectedDoc(e.target.value)}
          className="input-field max-w-xs text-sm"
        >
          <option value="">All Documents</option>
          {documents.map((doc) => (
            <option key={doc.id} value={doc.id}>
              {doc.filename}
            </option>
          ))}
        </select>
      </div>

      {/* ── Messages ─────────────────────────────── */}
      <div
        ref={scrollRef}
        className="glass-card flex-1 space-y-6 overflow-y-auto p-6"
      >
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-accent/10">
              <svg
                className="h-8 w-8 text-accent"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z"
                />
              </svg>
            </div>
            <p className="text-lg font-medium text-white/60">
              Ask a question about your documents
            </p>
            <p className="mt-1 text-sm text-white/30">
              Answers include citations from uploaded files
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "assistant" && (
              <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-accent/20">
                <svg
                  className="h-4 w-4 text-accent"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
                  />
                </svg>
              </div>
            )}

            <div
              className={`max-w-[75%] space-y-3 rounded-2xl px-5 py-3 ${
                msg.role === "user"
                  ? "bg-accent text-white"
                  : "border border-white/[0.06] bg-surface-100"
              }`}
            >
              <div className="prose-rag whitespace-pre-wrap text-sm leading-relaxed">
                {msg.content}
              </div>

              {/* Source citations */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="space-y-2 border-t border-white/[0.06] pt-3">
                  <p className="text-xs font-medium uppercase tracking-wider text-white/40">
                    Sources
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {msg.sources.map((src, i) => (
                      <button
                        key={i}
                        onClick={() =>
                          setExpandedSource(
                            expandedSource === `${msg.id}-${i}`
                              ? null
                              : `${msg.id}-${i}`
                          )
                        }
                        className="inline-flex items-center gap-1.5 rounded-lg border border-accent/20 bg-accent/5 px-2.5 py-1 text-xs text-accent-light transition-colors hover:bg-accent/10"
                      >
                        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                        </svg>
                        {src.filename} — p.{src.page_number}
                      </button>
                    ))}
                  </div>

                  {/* Expanded source preview */}
                  {msg.sources.map(
                    (src, i) =>
                      expandedSource === `${msg.id}-${i}` && (
                        <div
                          key={`expanded-${i}`}
                          className="animate-slide-up rounded-lg border border-white/[0.06] bg-surface-50 p-3 text-xs text-white/60"
                        >
                          <p className="mb-1 text-white/40">
                            Page {src.page_number} · Score: {src.score.toFixed(3)}
                          </p>
                          <p className="whitespace-pre-wrap">{src.chunk_text}</p>
                        </div>
                      )
                  )}
                </div>
              )}
            </div>

            {msg.role === "user" && (
              <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-white/10">
                <svg
                  className="h-4 w-4 text-white/60"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
                  />
                </svg>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-4">
            <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-accent/20">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
            </div>
            <div className="flex items-center gap-1.5 rounded-2xl border border-white/[0.06] bg-surface-100 px-5 py-3">
              <span className="h-2 w-2 animate-bounce rounded-full bg-white/30 [animation-delay:0ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-white/30 [animation-delay:150ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-white/30 [animation-delay:300ms]" />
            </div>
          </div>
        )}
      </div>

      {/* ── Input bar ────────────────────────────── */}
      <div className="mt-4 flex gap-3">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your documents…"
          rows={1}
          className="input-field flex-1 resize-none"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || loading}
          className="btn-primary px-5 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
