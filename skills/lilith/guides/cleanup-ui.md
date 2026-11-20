# UI and copy cleanup

Make the interface stop looking AI-generated. A good interface is used, not read: keep the words a person needs to act, cut the rest.

## The rules of the cut

- **Delete first, write little.** If you rewrite, use only facts already in the code: the product's own words, real feature names, real data. Never invent a number, a speed, an integration or a benefit.
- **Change text and decoration only.** No logic, data, layout or colors (except the surface rules in ui/surface.md, and only if the user asked for visual cleanup).
- **Never touch accessibility:** keep `aria-label`, `alt`, visible form labels, screen-reader text.
- **Claims you can't verify** (customer counts, ratings, testimonials, logos): don't edit. List as tasks.
- **A clean screen is a good result.** If there is nothing to cut, say so and change nothing.

Count before and after: `python3 <this-skill-folder>/scripts/count_tells.py <folder>` (add `--surface` for visual rules). It's a rough regex count that also flags fine cases; your reading is the real check.

Load more only when needed: [ui/charts.md](ui/charts.md) if the scanner lists a chart library or the screen has charts (U12 to U16); [ui/surface.md](ui/surface.md) only if the user asks for visual cleanup (U17 to U20); [ui/examples.md](ui/examples.md) when unsure how far to cut.

## Interface copy

- **U1. Eyebrow labels.** Small uppercase text above a heading ("FEATURES", "HOW IT WORKS", "● NEW"). Delete; the heading already says it.
- **U2. Decorative numbering.** "01 02 03", "01 // Features". Delete unless it's a real ordered process (checkout steps).
- **U3. Subtitle under everything.** "Analytics / Understand your data better". Keep a subtitle only if it states a fact the heading doesn't.
- **U4. Explaining the obvious.** "Click the button below to get started", "This chart shows revenue over time". Delete. Error and empty states stay, rewritten as one or two plain sentences: what happened, what to do. No "Oops!".
- **U5. Leaked design notes.** "(updates in real time)", "(powered by AI)". Delete or move to a tooltip.
- **U6. Status strings.** "12 items · Updated 2m ago · Synced · v2.1". Keep the one fact the user acts on.
- **U7. Labeling everything twice.** Placeholder repeating the label, helper text saying what the field obviously is. Keep one cue. Keep real constraints ("At least 12 characters").
- **U8. Empty slogans.** "Ship faster. Think less.", "Built different.", "One. Big. Thing." Rewrite as one sentence saying what the product does, or delete.

Length: card titles and section headings inside the app: 5 words or fewer.

## Decoration

Real state means the element renders from data (`{isLive && ...}`, a prop, a query). Fixed markup that always shows is decoration.

- **U9. Badges without real state.** "LIVE", "NEW", "AI", "Beta", "🔥 Popular" for flavor. Delete unless backed by data.
- **U10. Fake status dots.** Pulsing green dots next to text, wired to nothing. Delete. (Loading skeletons are fine.)
- **U11. Decorative emojis and icons.** In headings, buttons, feature lists, and the icon-in-a-colored-square above every feature card. Delete the icon and its box. Keep icons that are the control (icon button with `aria-label`) or that carry meaning.

## Copy rules (for every sentence you keep or write)

- **AI words:** cut or replace crucial, delve, enhance, seamless, showcase, pivotal, vibrant, landscape, testament, elevate, unlock, empower, revolutionize, cutting-edge, game-changer, leverage, utilize.
- **Say "is" and "has":** not "serves as", "boasts", "features".
- **Drop the "Not just X, but Y" frame.** Say the one thing that is true.
- **No forced groups of three.**
- **One name per thing.** Not workspace / project / space for the same thing.
- **No false ranges:** "From startups to enterprises". Name who it's for.
- **No em dashes** (—) in UI copy; use a period or comma. A lone "—" for an empty value is fine.
- **Sentence case**, not Title Case.
- **Cut filler:** "In order to" → "To"; delete "It's important to note that".
- **Describe the job, not the mood:** "Finance, simplified" → "Send invoices and track who paid". If the sentence fits any other product's page unchanged, cut it.
- **Active voice, short sentences, no adverbs** (seamlessly, effortlessly), **plain words** (use, help).

## Report for this part

A small table of rule, before, after. Then **Rewritten** (every string you wrote, old → new, so the owner can check it) and **Tasks** (claims to verify, text from a CMS or translation file, decisions for the owner).
