"use client";
import { useState } from "react";
import { marked } from "marked";

export default function ChatBox() {
  const [input, setInput] = useState("");
  const [answer, setAnswer] = useState("");

  async function send() {
    const res = await fetch("/api/chat", {
      method: "POST",
      body: JSON.stringify({ messages: [{ role: "user", content: input }] }),
    });
    const data = await res.json();
    setAnswer(data.answer);
  }

  return (
    <div>
      <textarea value={input} onChange={(e) => setInput(e.target.value)} />
      <button onClick={send}>Ask</button>
      <div className="prose" dangerouslySetInnerHTML={{ __html: marked.parse(answer) as string }} />
    </div>
  );
}
