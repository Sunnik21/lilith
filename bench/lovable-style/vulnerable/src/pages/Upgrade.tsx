import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import { stripePromise } from "@/lib/stripe";

export default function Upgrade() {
  const [params] = useSearchParams();

  useEffect(() => {
    if (params.get("success") === "true") {
      supabase.auth.getUser().then(({ data }) => {
        if (data.user) {
          supabase.from("profiles").update({ plan: "pro" }).eq("id", data.user.id);
        }
      });
    }
  }, [params]);

  async function checkout() {
    const stripe = await stripePromise;
    await stripe?.redirectToCheckout({
      lineItems: [{ price: "price_pro_monthly", quantity: 1 }],
      mode: "subscription",
      successUrl: `${window.location.origin}/upgrade?success=true`,
      cancelUrl: `${window.location.origin}/upgrade`,
    });
  }

  return <button onClick={checkout}>Upgrade to Pro</button>;
}
