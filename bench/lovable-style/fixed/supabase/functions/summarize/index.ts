import OpenAI from "npm:openai";
import { requireUser, rateLimit } from "../_shared/guard.ts";

const openai = new OpenAI({ apiKey: Deno.env.get("OPENAI_API_KEY") });

Deno.serve(async (req) => {
  const user = await requireUser(req);
  if (!user) return new Response("Unauthorized", { status: 401 });
  if (!(await rateLimit(user.id, "summarize", 20))) return new Response("Too many requests", { status: 429 });

  const { text } = await req.json();
  const res = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [{ role: "user", content: `Summarize this note:\n\n${String(text).slice(0, 8000)}` }],
  });
  return Response.json({ summary: res.choices[0].message.content ?? "" });
});
