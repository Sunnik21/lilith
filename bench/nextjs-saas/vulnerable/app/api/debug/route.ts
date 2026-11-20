import { NextResponse } from "next/server";

// Quick check that env vars are loaded on Vercel
export async function GET() {
  return NextResponse.json({ env: process.env, node: process.version });
}
