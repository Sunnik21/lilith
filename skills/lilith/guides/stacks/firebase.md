# Firebase details (load when the scanner detects Firebase)

## S3: rules
- `firestore.rules` / `storage.rules` / `database.rules.json` with `allow read, write: if true;`, `".read": true`, or a test-mode `request.time < timestamp.date(...)`: open to everyone.
- `if request.auth != null` on data that belongs to one user (users, orders, messages): any logged-in user can read or change everyone's data, and signing up is free.
- A wildcard `match /{document=**}` with a broad `allow` covers every collection, including future ones.
- Deployed rules can differ from the repo: follow `checks/firebase_check.md` (the user pastes the live rules).

## S4
Server code must verify the ID token (`admin.auth().verifyIdToken`) before trusting a user id.

## S10
`storage.rules` should limit each user to their own path (`request.auth.uid == userId`).
