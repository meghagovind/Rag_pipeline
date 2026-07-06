/**
 * Storage utility — uploads files to Vercel Blob (production) or
 * saves to local filesystem (development fallback).
 */

import { put } from "@vercel/blob";
import { writeFile, mkdir } from "fs/promises";
import path from "path";

const BLOB_TOKEN = process.env.BLOB_READ_WRITE_TOKEN;
const IS_VERCEL_DEPLOYMENT = process.env.VERCEL === "1";

export async function uploadFile(
  file: File
): Promise<{ url: string; pathname: string }> {
  // ── Vercel Blob (production) ──────────────────────
  if (IS_VERCEL_DEPLOYMENT && BLOB_TOKEN) {
    const blob = await put(file.name, file, {
      access: "public",
      token: BLOB_TOKEN,
    });
    return { url: blob.url, pathname: blob.pathname };
  }

  // ── Local filesystem fallback (development) ───────
  const uploadsDir = path.join(process.cwd(), "uploads");
  await mkdir(uploadsDir, { recursive: true });

  const filePath = path.join(uploadsDir, `${Date.now()}-${file.name}`);
  const buffer = Buffer.from(await file.arrayBuffer());
  await writeFile(filePath, buffer);

  return { url: filePath, pathname: file.name };
}
