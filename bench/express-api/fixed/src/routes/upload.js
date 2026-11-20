const express = require("express");
const multer = require("multer");
const path = require("path");
const crypto = require("crypto");
const { requireAuth } = require("../middleware/auth");

const ALLOWED = { "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp" };

const storage = multer.diskStorage({
  destination: path.join(__dirname, "../../public/uploads"),
  filename: (req, file, cb) => cb(null, crypto.randomUUID() + ALLOWED[file.mimetype]),
});
const upload = multer({
  storage,
  limits: { fileSize: 2 * 1024 * 1024 },
  fileFilter: (req, file, cb) => cb(null, file.mimetype in ALLOWED),
});

const router = express.Router();

router.post("/avatar", requireAuth, upload.single("file"), (req, res) => {
  if (!req.file) return res.status(400).json({ error: "PNG, JPG or WebP up to 2 MB" });
  res.json({ url: `/uploads/${req.file.filename}` });
});

module.exports = router;
