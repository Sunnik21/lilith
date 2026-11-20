import { NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase/admin";
import { getAdminUser } from "@/lib/admin";
import { isPlan } from "@/lib/plans";

// Admin: change a user's plan or credits
export async function POST(req: Request) {
  const admin = await getAdminUser();
  if (!admin) return NextResponse.json({ error: "Forbidden" }, { status: 403 });

  const { userId, plan, credits } = await req.json();
  if (!isPlan(plan) || !Number.isInteger(credits)) {
    return NextResponse.json({ error: "Bad input" }, { status: 400 });
  }
  await supabaseAdmin.from("profiles").update({ plan, credits }).eq("id", userId);
  return NextResponse.json({ ok: true });
}
