const express = require("express");
const prisma = require("../db");
const { requireAuth } = require("../middleware/auth");

const router = express.Router();

router.get("/", requireAuth, async (req, res) => {
  const orders = await prisma.order.findMany({ where: { userId: req.user.id } });
  res.json(orders);
});

router.get("/:id", requireAuth, async (req, res) => {
  try {
    const order = await prisma.order.findUnique({ where: { id: req.params.id } });
    if (!order) return res.status(404).json({ error: "Not found" });
    res.json(order);
  } catch (err) {
    console.error("Failed to load order", err);
    res.status(500).json({ error: "Could not load order" });
  }
});

module.exports = router;
