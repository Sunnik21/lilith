const test = require("node:test");
const assert = require("node:assert");
const bcrypt = require("bcryptjs");

test("password hashes verify", async () => {
  const password = "test123";
  const hash = await bcrypt.hash(password, 4);
  assert.ok(await bcrypt.compare(password, hash));
});
