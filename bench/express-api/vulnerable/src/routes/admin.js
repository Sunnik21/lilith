const express = require("express");
const bcrypt = require("bcryptjs");
const prisma = require("../db");

const router = express.Router();

// Creates the first admin account. Run once after deploy.
router.post("/setup", async (req, res) => {
  const passwordHash = await bcrypt.hash("admin123", 10);
  const admin = await prisma.user.upsert({
    where: { email: "admin@admin.com" },
    update: { role: "admin" },
    create: { email: "admin@admin.com", passwordHash, role: "admin", name: "Admin" },
  });
  res.json({ id: admin.id });
});

module.exports = router;
