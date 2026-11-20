import OpenAI from "openai";
import { createClient } from "@/lib/supabase/server";
import { SYSTEM_PROMPT } from "@/lib/ai/prompt";
import { chatRatelimit } from "@/lib/ratelimit";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

export async function POST(req: Request) {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return new Response("Unauthorized", { status: 401 });

  const { success } = await chatRatelimit.limit(user.id);
  if (!success) return new Response("Too many requests", { status: 429 });

  const { message } = await req.json();
  const completion = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    max_tokens: 800,
    messages: [{ role: "system", content: SYSTEM_PROMPT }, { role: "user", content: String(message).slice(0, 4000) }],
  });
  return Response.json({ answer: completion.choices[0].message.content });
}
