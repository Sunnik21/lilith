const express = require("express");
const multer = require("multer");
const path = require("path");
const { requireAuth } = require("../middleware/auth");

const storage = multer.diskStorage({
  destination: path.join(__dirname, "../../public/uploads"),
  filename: (req, file, cb) => cb(null, file.originalname),
});
const upload = multer({ storage });

const router = express.Router();

router.post("/avatar", requireAuth, upload.single("file"), (req, res) => {
  res.json({ url: `/uploads/${req.file.originalname}` });
});

module.exports = router;
