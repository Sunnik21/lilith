"use client";
import { deleteProject } from "@/app/actions/projects";

export default function ProjectList({ projects }: { projects: { id: string; name: string }[] }) {
  return (
    <ul>
      {projects.map((p) => (
        <li key={p.id}>
          {p.name} <button onClick={() => deleteProject(p.id)}>Delete</button>
        </li>
      ))}
    </ul>
  );
}
