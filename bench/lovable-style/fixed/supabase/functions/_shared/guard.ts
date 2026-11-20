import { createClient } from "npm:@supabase/supabase-js@2";

const admin = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

// Returns the logged-in user, or null.
export async function requireUser(req: Request) {
  const token = (req.headers.get("Authorization") ?? "").replace("Bearer ", "");
  const { data } = await admin.auth.getUser(token);
  return data.user ?? null;
}

// Simple per-user rate limit: max `limit` calls of `action` per hour.
export async function rateLimit(userId: string, action: string, limit: number) {
  const since = new Date(Date.now() - 60 * 60 * 1000).toISOString();
  const { count } = await admin.from("usage").select("*", { count: "exact", head: true })
    .eq("user_id", userId).eq("action", action).gte("created_at", since);
  if ((count ?? 0) >= limit) return false;
  await admin.from("usage").insert({ user_id: userId, action });
  return true;
}
