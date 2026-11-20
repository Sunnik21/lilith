"use client";
import { loadStripe } from "@stripe/stripe-js";

const stripePromise = loadStripe("{{STRIPE_PK}}");

export default function Pricing() {
  async function buy(plan: "starter" | "pro") {
    const res = await fetch("/api/checkout", { method: "POST", body: JSON.stringify({ plan }) });
    const { url } = await res.json();
    await stripePromise;
    window.location.href = url;
  }
  return (
    <div>
      <button onClick={() => buy("starter")}>Starter $9</button>
      <button onClick={() => buy("pro")}>Pro $29</button>
    </div>
  );
}
