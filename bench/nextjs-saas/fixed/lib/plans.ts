// Prices live on the server. The browser only sends the plan name.
export const PLANS = {
  starter: { stripePriceId: "price_starter_monthly", credits: 200 },
  pro: { stripePriceId: "price_pro_monthly", credits: 1000 },
} as const;

export type PlanName = keyof typeof PLANS;

export function isPlan(value: unknown): value is PlanName {
  return typeof value === "string" && value in PLANS;
}
