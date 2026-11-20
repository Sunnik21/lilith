// Run once from your own machine: ADMIN_EMAIL=you@yourdomain.com ADMIN_PASSWORD=... node scripts/create-admin.js
const bcrypt = require("bcryptjs");
const prisma = require("../src/db");

async function main() {
  const email = process.env.ADMIN_EMAIL;
  const pass = process.env.ADMIN_PASSWORD;
  if (!email || !pass || pass.length < 12) throw new Error("Set ADMIN_EMAIL and ADMIN_PASSWORD (12+ characters)");
  const passwordHash = await bcrypt.hash(pass, 12);
  await prisma.user.upsert({ where: { email }, update: { role: "admin" }, create: { email, passwordHash, role: "admin" } });
}

main().finally(() => prisma.$disconnect());
