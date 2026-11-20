"use client";
import { useState } from "react";
import ReactMarkdown from "react-markdown";

export default function ChatBox() {
  const [input, setInput] = useState("");
  const [answer, setAnswer] = useState("");

  async function send() {
    const res = await fetch("/api/chat", { method: "POST", body: JSON.stringify({ message: input }) });
    const data = await res.json();
    setAnswer(data.answer);
  }

  return (
    <div>
      <textarea value={input} onChange={(e) => setInput(e.target.value)} />
      <button onClick={send}>Ask</button>
      {/* react-markdown renders text safely: no raw HTML */}
      <div className="prose"><ReactMarkdown>{answer}</ReactMarkdown></div>
    </div>
  );
}
