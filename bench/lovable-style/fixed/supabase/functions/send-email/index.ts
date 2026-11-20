import { Resend } from "npm:resend";
import { requireUser, rateLimit } from "../_shared/guard.ts";

const resend = new Resend(Deno.env.get("RESEND_API_KEY"));

// Sends a copy of a note to the logged-in user's own address only.
Deno.serve(async (req) => {
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405 });
  const user = await requireUser(req);
  if (!user?.email) return new Response("Unauthorized", { status: 401 });
  if (!(await rateLimit(user.id, "email", 5))) return new Response("Too many requests", { status: 429 });

  const { subject, text } = await req.json();
  const { data, error } = await resend.emails.send({
    from: "NoteNest <hello@notenest.app>",
    to: user.email,
    subject: String(subject).slice(0, 200),
    text: String(text).slice(0, 10000),
  });
  if (error) return new Response("Could not send", { status: 400 });
  return Response.json({ id: data?.id });
});
