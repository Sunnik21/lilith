# Live rules check for Firebase

The rules file in the repo (`firestore.rules`, `storage.rules`, `database.rules.json`) is not always what is running. Rules can be edited in the console, or the file was never deployed. The rules that protect the data are the **deployed** ones, so check those.

## What to ask the user (2 minutes)

Say, in their language:

> Your app's data is protected by "rules" stored in Firebase. I'll check the ones that are live right now. Copying them is safe: rules are settings, not your users' data.
>
> 1. Open console.firebase.google.com and pick your project.
> 2. **Firestore Database → Rules** tab. Copy everything in the editor and paste it here.
> 3. If you use them, do the same for **Storage → Rules** and **Realtime Database → Rules**.
>
> If you'd rather skip this, say "skip" and I'll mark the live rules as not checked.

## What to do with the pasted rules

1. **Compare with the repo.** If the repo has a rules file, diff it against the pasted text. If they differ, say so in one line: "The rules running now are not the ones in your code." The live rules decide what's protected, so judge those. Suggest deploying from the repo afterward (`firebase deploy --only firestore:rules,storage`) so they stay in sync.
2. **Apply the S3 patterns** from [../guides/stacks/firebase.md](../guides/stacks/firebase.md) to the live rules:

| Pattern in live rules | Severity | Plain meaning |
|---|---|---|
| `allow read, write: if true;` (or `allow write: if true`) | 🔴 Critical | Anyone on the internet can read and change this data. |
| `".read": true` / `".write": true` (Realtime Database) | 🔴 Critical | Same, for Realtime Database. |
| `request.time < timestamp.date(...)` | 🔴 Critical | "Test mode": open to everyone until that date, then the app breaks. |
| `if request.auth != null` on data that belongs to one user (`users`, `orders`, `messages`, `profiles`) | 🟠 High | Any logged-in user can read or change every other user's data. Signing up is free, so this is close to open. |
| `allow read: if true` on truly public data (blog posts, product list) with no write rule for everyone | 💡 Fine | Say it's OK and why. |
| A wildcard `match /{document=**}` with a broad `allow` | 🔴/🟠 | That rule covers every collection, including ones added later. |

3. **Report** each problem in the normal what / why / fix format. The fix is a rule that ties data to its owner:

```
match /orders/{orderId} {
  allow read, update, delete: if request.auth != null && request.auth.uid == resource.data.userId;
  allow create: if request.auth != null && request.auth.uid == request.resource.data.userId;
}
```

4. In the report header write **Live database: checked (Firebase rules pasted on <date>)**. If the user skipped, write **Live database: NOT checked** and add the steps above to "Only you can do this".

## Limits

- Pasted rules show what's allowed, not what data exists. A collection with no rule is denied by default, which is safe.
- Firebase App Check and API key restrictions live elsewhere in the console. Mention them under "Nice to have" only.
