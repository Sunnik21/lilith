"use server";
import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";

export async function deleteProject(projectId: string) {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error("Not logged in");
  // User's own client: RLS only lets owners delete their projects.
  await supabase.from("projects").delete().eq("id", projectId).eq("owner_id", user.id);
  revalidatePath("/dashboard");
}
