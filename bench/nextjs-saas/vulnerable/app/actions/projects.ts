"use server";
import { revalidatePath } from "next/cache";
import { supabaseAdmin } from "@/lib/supabase/admin";

export async function deleteProject(projectId: string) {
  await supabaseAdmin.from("documents").delete().eq("project_id", projectId);
  await supabaseAdmin.from("projects").delete().eq("id", projectId);
  revalidatePath("/dashboard");
}
