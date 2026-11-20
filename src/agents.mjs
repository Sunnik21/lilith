// Where each coding agent looks for Agent Skills.
// Paths match the `skills` CLI (npm: skills), so both installers agree.
import { join } from "node:path";

export function agentTable(env, home) {
  const claudeHome = env.CLAUDE_CONFIG_DIR?.trim() || join(home, ".claude");
  const codexHome = env.CODEX_HOME?.trim() || join(home, ".codex");
  const configHome = env.XDG_CONFIG_HOME?.trim() || join(home, ".config");

  return Object.freeze({
    claude: {
      name: "Claude Code",
      globalDir: join(claudeHome, "skills"),
      projectDir: ".claude/skills",
      detectDir: claudeHome,
    },
    codex: {
      name: "Codex",
      globalDir: join(home, ".agents", "skills"),
      projectDir: ".agents/skills",
      detectDir: codexHome,
    },
    cursor: {
      name: "Cursor",
      globalDir: join(home, ".cursor", "skills"),
      projectDir: ".agents/skills",
      detectDir: join(home, ".cursor"),
    },
    gemini: {
      name: "Gemini CLI",
      globalDir: join(home, ".gemini", "skills"),
      projectDir: ".agents/skills",
      detectDir: join(home, ".gemini"),
    },
    copilot: {
      name: "GitHub Copilot",
      globalDir: join(home, ".copilot", "skills"),
      projectDir: ".agents/skills",
      detectDir: join(home, ".copilot"),
    },
    opencode: {
      name: "OpenCode",
      globalDir: join(configHome, "opencode", "skills"),
      projectDir: ".agents/skills",
      detectDir: join(configHome, "opencode"),
    },
    windsurf: {
      name: "Windsurf",
      globalDir: join(home, ".codeium", "windsurf", "skills"),
      projectDir: ".windsurf/skills",
      detectDir: join(home, ".codeium", "windsurf"),
    },
  });
}
