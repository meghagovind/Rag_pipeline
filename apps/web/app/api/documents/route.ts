import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export const runtime = "nodejs";

export async function GET() {
  try {
    const documents = await prisma.document.findMany({
      orderBy: { createdAt: "desc" },
      select: {
        id: true,
        filename: true,
        fileUrl: true,
        status: true,
        createdAt: true,
      },
    });

    return NextResponse.json({ documents });
  } catch (err) {
    console.error("Documents list error:", err);
    return NextResponse.json(
      { error: "Internal server error", documents: [] },
      { status: 500 }
    );
  }
}
