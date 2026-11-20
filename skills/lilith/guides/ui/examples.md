# Before and after

Read when unsure how far to cut.

**Hero with eyebrow (U1, U3, U8)**
```html
<p class="text-xs uppercase tracking-widest">Introducing Ledger</p>
<h1>Finance. Simplified. Finally.</h1>
<p>The all-in-one platform that helps modern teams seamlessly manage their money.</p>
```
→ `<h1>Manage your team's money</h1>`. The eyebrow goes; the slogan becomes the one thing the subtitle actually said; nothing new is invented (no numbers, no features the page doesn't name).

**Numbered feature (U2, U4)**
`<span>01 //</span><h3>Smart sync</h3><p>Our smart sync feature automatically keeps your files in sync across all of your devices.</p>`
→ `<h3>Smart sync</h3><p>Your files stay in sync across your devices.</p>`. The order isn't real, so the number goes; the description keeps only what the title doesn't say.

**Card that explains itself (U4, U5)**
`<CardDescription>This card shows your most recent activity (updates in real time).</CardDescription>` → delete it; the title "Recent activity" and the list say it.

**Badge with and without state (U9)**
`<Badge>LIVE</Badge>` always rendered → delete. `{stream.isLive && <Badge>Live</Badge>}` → keep: it reflects real state.

**Form field (U7)**
Label "Email", placeholder "Enter your email address", helper "We'll use this email to contact you" → keep the visible label; the placeholder becomes a format (`name@company.com`) or goes; the helper goes. A real constraint ("At least 12 characters") stays.

**Empty state (U4)**
"Oops! Looks like there's nothing here yet! 🎉" → "No invoices yet. Create one to send it to a client."

**Claim you cannot verify**
"Trusted by 10,000+ teams", a testimonial with a name → don't edit or delete; list as a task for the owner to confirm or remove.
