import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { summarize } from "@/lib/ai";

type Comment = { id: string; author: string; body: string };

export default function Comments({ postId }: { postId: string }) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [summary, setSummary] = useState("");

  useEffect(() => {
    supabase.from("messages").select("*").eq("post_id", postId).then(({ data }) => setComments(data ?? []));
  }, [postId]);

  return (
    <section>
      {comments.map((c) => (
        <div key={c.id}>
          <strong>{c.author}</strong>
          <p>{c.body}</p>
        </div>
      ))}
      <button onClick={async () => setSummary(await summarize(comments.map((c) => c.body).join("\n")))}>
        Summarize
      </button>
      <p>{summary}</p>
    </section>
  );
}
