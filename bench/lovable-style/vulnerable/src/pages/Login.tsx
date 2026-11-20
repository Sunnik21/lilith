import { useState } from "react";
import { supabase } from "@/lib/supabase";

const DEMO_ACCOUNT = { email: "admin@admin.com", password: "admin123" };

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function signIn(creds = { email, password }) {
    const { error } = await supabase.auth.signInWithPassword(creds);
    if (error) alert(error.message);
    else window.location.href = "/";
  }

  return (
    <form onSubmit={(e) => { e.preventDefault(); signIn(); }}>
      <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
      <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <button type="submit">Sign in</button>
      <button type="button" onClick={() => signIn(DEMO_ACCOUNT)}>Try the demo</button>
    </form>
  );
}
