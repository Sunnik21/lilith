import { NextResponse } from "next/server";
import { stripe } from "@/lib/stripe";
import { createClient } from "@/lib/supabase/server";
import { PLANS, isPlan } from "@/lib/plans";

export async function POST(req: Request) {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { plan } = await req.json();
  if (!isPlan(plan)) return NextResponse.json({ error: "Unknown plan" }, { status: 400 });

  const session = await stripe.checkout.sessions.create({
    mode: "subscription",
    customer_email: user.email,
    client_reference_id: user.id,
    metadata: { plan },
    line_items: [{ quantity: 1, price: PLANS[plan].stripePriceId }],
    success_url: `${process.env.NEXT_PUBLIC_SITE_URL}/dashboard?paid=1`,
    cancel_url: `${process.env.NEXT_PUBLIC_SITE_URL}/pricing`,
  });
  return NextResponse.json({ url: session.url });
}
