import { NextResponse, type NextRequest } from "next/server";

const ALLOWED_ORIGINS = new Set(["https://docuflow.app", "https://www.docuflow.app"]);

// Only our own sites may call the API with the user's cookies
export function middleware(req: NextRequest) {
  const origin = req.headers.get("origin");
  const res = req.method === "OPTIONS" ? new NextResponse(null, { status: 204 }) : NextResponse.next();
  if (origin && ALLOWED_ORIGINS.has(origin)) {
    res.headers.set("Access-Control-Allow-Origin", origin);
    res.headers.set("Access-Control-Allow-Credentials", "true");
    res.headers.set("Vary", "Origin");
  }
  return res;
}

export const config = { matcher: "/api/:path*" };
