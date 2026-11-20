const express = require("express");

const router = express.Router();

// Used by the load balancer. Public on purpose, returns no data.
router.get("/", (req, res) => {
  res.json({ status: "ok" });
});

module.exports = router;
