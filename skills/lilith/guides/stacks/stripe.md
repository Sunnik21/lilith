# Stripe and payments details (load when the scanner detects Stripe or another payment provider)

## S6
- `unit_amount`, `price` or `amount` taken from the request body: look prices up on the server (Stripe Price IDs or your database).
- Plans and credits granted from request fields instead of from the verified payment.

## S7
- Webhook handlers need `stripe.webhooks.constructEvent(rawBody, signature, whsec)` (or `constructEventAsync`). Lemon Squeezy, Paddle, Clerk (svix) and GitHub have their own signature checks.
- Signature verification needs the raw body: `req.text()` / `express.raw`, not `req.json()` first.
- Access must be granted only from the verified webhook. A success page (`?success=true`, `?paid=1`) that updates the plan lets anyone skip paying.

## Not secrets
Stripe publishable keys (`pk_live_`, `pk_test_`) belong in the browser.
