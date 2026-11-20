import { NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase/admin";

// Admin: change a user's plan or credits
export async function POST(req: Request) {
  const { requesterRole, userId, plan, credits } = await req.json();
  if (requesterRole !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }
  await supabaseAdmin.from("profiles").update({ plan, credits }).eq("id", userId);
  return NextResponse.json({ ok: true });
}
