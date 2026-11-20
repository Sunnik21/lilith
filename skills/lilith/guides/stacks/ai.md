# AI API details (load when the scanner detects OpenAI, Anthropic or another AI SDK)

## S2
`new OpenAI(` / `new Anthropic(` in browser code, `dangerouslyAllowBrowser: true`, `VITE_OPENAI_API_KEY`, direct calls to `api.openai.com` from React: the key ships to every visitor.

## S8 (🟠 for AI endpoints)
- Require login for AI endpoints and add a per-user limit; cap `max_tokens` and the length of user input.
- Clients that send the whole message history let one user grow every request.
- Owner checklist: monthly spending limit in the AI provider dashboard.

## S9 / S11
- Model output rendered with `dangerouslySetInnerHTML` or a Markdown renderer allowing raw HTML: prompt-injected documents can run script.
- System prompts with discount codes, internal URLs or logins: any user can extract them.
- Tools that write data or send messages: scope them to the current user and ask before acting.
