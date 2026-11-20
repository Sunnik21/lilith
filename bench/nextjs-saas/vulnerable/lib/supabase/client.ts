"use client";
import { createBrowserClient } from "@supabase/ssr";

export const supabase = createBrowserClient(
  "https://qrstuvwxyzabcdef.supabase.co",
  "{{ANON_JWT}}"
);
