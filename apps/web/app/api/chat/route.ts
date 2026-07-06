import { NextRequest, NextResponse } from "next/server";
import { queryRAG } from "@/lib/rag";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { question, document_id } = body;

    if (!question || typeof question !== "string") {
      return NextResponse.json(
        { error: "question is required" },
        { status: 400 }
      );
    }

    const result = await queryRAG(question, document_id || undefined);

    return NextResponse.json({
      answer: result.answer,
      sources: result.sources,
    });
  } catch (err) {
    console.error("Chat error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
