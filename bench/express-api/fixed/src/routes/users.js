const express = require("express");
const prisma = require("../db");
const { requireAuth } = require("../middleware/auth");

const router = express.Router();

router.get("/me", requireAuth, async (req, res) => {
  const user = await prisma.user.findUnique({
    where: { id: req.user.id },
    select: { id: true, email: true, name: true, role: true },
  });
  res.json(user);
});

// Users can change only their own name.
router.patch("/me", requireAuth, async (req, res) => {
  const name = typeof req.body.name === "string" ? req.body.name.slice(0, 100) : undefined;
  const user = await prisma.user.update({
    where: { id: req.user.id },
    data: { name },
  });
  res.json({ id: user.id, name: user.name });
});

module.exports = router;
