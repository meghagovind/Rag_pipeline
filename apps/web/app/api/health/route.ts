import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET() {
  return NextResponse.json({
    status: "healthy",
    service: "web",
    timestamp: new Date().toISOString(),
  });
}
