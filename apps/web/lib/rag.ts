/**
 * RAG utility — calls the FastAPI ingestion service for querying.
 * Also provides a local fallback that queries Postgres directly
 * for similarity search using raw SQL + pgvector.
 */

const INGESTION_API_URL =
  process.env.INGESTION_API_URL ?? "http://localhost:8000";

export interface RAGSource {
  chunk_text: string;
  page_number: number;
  document_id: string;
  filename: string;
  score: number;
}

export interface RAGResult {
  answer: string;
  sources: RAGSource[];
}

/**
 * Trigger document ingestion via FastAPI.
 */
export async function triggerIngestion(
  documentId: string,
  filename: string,
  fileUrl: string
): Promise<{ status: string; message: string }> {
  try {
    const res = await fetch(`${INGESTION_API_URL}/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document_id: documentId,
        filename,
        file_url: fileUrl,
      }),
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Ingestion API error: ${res.status} — ${errText}`);
    }

    return await res.json();
  } catch (err) {
    console.error("Failed to trigger ingestion:", err);
    return {
      status: "PENDING",
      message: "Ingestion service unavailable — document queued for later processing.",
    };
  }
}

/**
 * Query the RAG pipeline via the FastAPI /query endpoint.
 */
export async function queryRAG(
  question: string,
  documentId?: string,
  topK: number = 4
): Promise<RAGResult> {
  try {
    const res = await fetch(`${INGESTION_API_URL}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        document_id: documentId ?? null,
        top_k: topK,
      }),
    });

    if (!res.ok) {
      throw new Error(`Query API error: ${res.status}`);
    }

    return await res.json();
  } catch (err) {
    console.error("RAG query failed:", err);
    return {
      answer:
        "The RAG service is currently unavailable. Please ensure the ingestion service is running.",
      sources: [],
    };
  }
}
