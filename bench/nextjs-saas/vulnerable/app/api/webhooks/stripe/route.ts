import { NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase/admin";

export async function POST(req: Request) {
  const event = await req.json();

  if (event.type === "checkout.session.completed") {
    const session = event.data.object;
    await supabaseAdmin
      .from("profiles")
      .update({ plan: "pro", credits: 1000 })
      .eq("id", session.client_reference_id);
  }

  return NextResponse.json({ received: true });
}
