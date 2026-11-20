import { NextResponse } from "next/server";
import { stripe } from "@/lib/stripe";
import { createClient } from "@/lib/supabase/server";

export async function POST(req: Request) {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { plan, price } = await req.json();
  const session = await stripe.checkout.sessions.create({
    mode: "payment",
    customer_email: user.email,
    client_reference_id: user.id,
    line_items: [{
      quantity: 1,
      price_data: { currency: "usd", unit_amount: price, product_data: { name: `DocuFlow ${plan}` } },
    }],
    success_url: `${process.env.NEXT_PUBLIC_SITE_URL}/dashboard?paid=1`,
    cancel_url: `${process.env.NEXT_PUBLIC_SITE_URL}/pricing`,
  });
  return NextResponse.json({ url: session.url });
}
