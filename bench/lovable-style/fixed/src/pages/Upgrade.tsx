import { useSearchParams } from "react-router-dom";
import { stripePromise } from "@/lib/stripe";

// The plan is changed only by the verified Stripe webhook (supabase/functions/stripe-webhook).
export default function Upgrade() {
  const [params] = useSearchParams();

  async function checkout() {
    const stripe = await stripePromise;
    await stripe?.redirectToCheckout({
      lineItems: [{ price: "price_pro_monthly", quantity: 1 }],
      mode: "subscription",
      successUrl: `${window.location.origin}/upgrade?success=true`,
      cancelUrl: `${window.location.origin}/upgrade`,
    });
  }

  if (params.get("success") === "true") return <p>Thanks! Your plan updates in a few seconds.</p>;
  return <button onClick={checkout}>Upgrade to Pro</button>;
}
