import { supabase } from "@/lib/supabase";

// The OpenAI key lives only in the Edge Function (supabase/functions/summarize).
export async function summarize(text: string) {
  const { data, error } = await supabase.functions.invoke("summarize", { body: { text } });
  if (error) throw error;
  return (data?.summary as string) ?? "";
}
