"use client";

import { useCallback, useState } from "react";

type UploadStatus = "idle" | "uploading" | "success" | "error";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [message, setMessage] = useState("");
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) {
      setFile(e.dataTransfer.files[0]);
      setStatus("idle");
      setMessage("");
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setFile(e.target.files[0]);
      setStatus("idle");
      setMessage("");
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setStatus("uploading");
    setMessage("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error ?? "Upload failed");
      }

      setStatus("success");
      setMessage(
        `Document uploaded successfully! ID: ${data.documentId}. Ingestion has started.`
      );
      setFile(null);
    } catch (err: unknown) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "Upload failed");
    }
  };

  return (
    <div className="animate-fade-in mx-auto max-w-2xl space-y-8">
      <div className="text-center">
        <h1 className="font-display text-4xl font-bold">Upload Document</h1>
        <p className="mt-2 text-white/50">
          Upload a PDF to extract, index, and chat with its contents.
        </p>
      </div>

      {/* ── Drop zone ────────────────────────────── */}
      <div
        className={`glass-card relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-12 text-center transition-all duration-300 ${
          dragActive
            ? "border-accent bg-accent/5 shadow-[0_0_40px_rgba(108,99,255,0.15)]"
            : "border-white/10 hover:border-white/20"
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
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
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
            />
          </svg>
        </div>

        {file ? (
          <div className="space-y-2">
            <p className="font-medium text-white/90">{file.name}</p>
            <p className="text-sm text-white/40">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-white/70">
              <span className="font-medium text-accent">Click to upload</span>{" "}
              or drag &amp; drop
            </p>
            <p className="text-sm text-white/30">PDF files up to 50 MB</p>
          </div>
        )}

        <input
          id="file-upload"
          type="file"
          accept=".pdf"
          className="absolute inset-0 cursor-pointer opacity-0"
          onChange={handleFileChange}
        />
      </div>

      {/* ── Upload button ────────────────────────── */}
      <button
        onClick={handleUpload}
        disabled={!file || status === "uploading"}
        className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-40"
      >
        {status === "uploading" ? (
          <>
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
            Processing…
          </>
        ) : (
          <>
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
                d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
              />
            </svg>
            Upload &amp; Ingest
          </>
        )}
      </button>

      {/* ── Status message ────────────────────────── */}
      {message && (
        <div
          className={`animate-slide-up rounded-xl p-4 text-sm ${
            status === "success"
              ? "border border-success/20 bg-success/10 text-success"
              : "border border-danger/20 bg-danger/10 text-danger"
          }`}
        >
          {message}
        </div>
      )}
    </div>
  );
}
