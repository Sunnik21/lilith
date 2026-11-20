import { loadStripe } from "@stripe/stripe-js";

export const stripePromise = loadStripe("{{STRIPE_PK}}");
