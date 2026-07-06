import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { uploadFile } from "@/lib/storage";
import { triggerIngestion } from "@/lib/rag";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get("file") as File | null;

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      return NextResponse.json(
        { error: "Only PDF files are supported" },
        { status: 400 }
      );
    }

    // 1. Upload file to storage
    const { url } = await uploadFile(file);

    // 2. Create document record
    const document = await prisma.document.create({
      data: {
        filename: file.name,
        fileUrl: url,
        status: "PENDING",
      },
    });

    // 3. Create ingestion job
    await prisma.ingestionJob.create({
      data: {
        documentId: document.id,
        status: "PENDING",
      },
    });

    // 4. Wait only for the ingestion service to accept the background job.
    // A detached fetch can be cancelled when a serverless request finishes.
    const ingestion = await triggerIngestion(document.id, file.name, url);

    return NextResponse.json({
      documentId: document.id,
      filename: file.name,
      status: ingestion.status,
      message: ingestion.message,
    });
  } catch (err) {
    console.error("Upload error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
