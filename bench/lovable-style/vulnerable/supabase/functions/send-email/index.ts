import { Resend } from "npm:resend";

const resend = new Resend(Deno.env.get("RESEND_API_KEY"));

Deno.serve(async (req) => {
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405 });
  const { to, subject, html } = await req.json();
  const { data, error } = await resend.emails.send({
    from: "NoteNest <hello@notenest.app>",
    to,
    subject,
    html,
  });
  if (error) return new Response(JSON.stringify(error), { status: 400 });
  return new Response(JSON.stringify(data), { headers: { "Content-Type": "application/json" } });
});
