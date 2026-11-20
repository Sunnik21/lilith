import { NextResponse, type NextRequest } from "next/server";

// Allow the Chrome extension and partner sites to call the API
export function middleware(req: NextRequest) {
  const origin = req.headers.get("origin") ?? "*";
  const res = req.method === "OPTIONS" ? new NextResponse(null, { status: 204 }) : NextResponse.next();
  res.headers.set("Access-Control-Allow-Origin", origin);
  res.headers.set("Access-Control-Allow-Credentials", "true");
  res.headers.set("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS");
  res.headers.set("Access-Control-Allow-Headers", "Content-Type, Authorization");
  return res;
}

export const config = { matcher: "/api/:path*" };
