import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

// Public list of published blog posts, no login needed.
export async function GET() {
  const supabase = createClient();
  const { data } = await supabase
    .from("posts")
    .select("slug, title, excerpt, published_at")
    .eq("published", true)
    .order("published_at", { ascending: false });
  return NextResponse.json(data ?? []);
}
