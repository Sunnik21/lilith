const express = require("express");
const prisma = require("../db");

const router = express.Router();

// Public product search
router.get("/", async (req, res) => {
  const q = req.query.q || "";
  const products = await prisma.$queryRawUnsafe(
    `SELECT id, name, price FROM "Product" WHERE name ILIKE '%${q}%' LIMIT 20`
  );
  res.json(products);
});

module.exports = router;
