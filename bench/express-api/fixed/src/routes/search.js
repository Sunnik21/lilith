const express = require("express");
const prisma = require("../db");

const router = express.Router();

// Public product search
router.get("/", async (req, res) => {
  const q = String(req.query.q || "").slice(0, 100);
  const products = await prisma.product.findMany({
    where: { name: { contains: q, mode: "insensitive" } },
    select: { id: true, name: true, price: true },
    take: 20,
  });
  res.json(products);
});

module.exports = router;
