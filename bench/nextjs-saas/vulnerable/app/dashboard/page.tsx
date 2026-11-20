import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import ChatBox from "@/components/ChatBox";
import ProjectList from "@/components/ProjectList";

export default async function Dashboard() {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  const { data: projects } = await supabase.from("projects").select("id, name").eq("owner_id", user.id);
  return (
    <main>
      <ProjectList projects={projects ?? []} />
      <ChatBox />
    </main>
  );
}
