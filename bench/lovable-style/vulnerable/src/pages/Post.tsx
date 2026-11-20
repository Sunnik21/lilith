import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import Comments from "@/components/Comments";

export default function Post() {
  const { id } = useParams();
  const [post, setPost] = useState<{ title: string; body: string } | null>(null);

  useEffect(() => {
    supabase.from("posts").select("title, body").eq("id", id).single().then(({ data }) => setPost(data));
  }, [id]);

  if (!post) return null;
  return (
    <article>
      <h1>{post.title}</h1>
      <p>{post.body}</p>
      <Comments postId={id!} />
    </article>
  );
}
