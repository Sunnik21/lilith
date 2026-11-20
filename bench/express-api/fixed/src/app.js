const express = require("express");
const cors = require("cors");
const path = require("path");
const config = require("./config");

const app = express();

app.use(cors({ origin: config.allowedOrigins, credentials: true }));
app.use(express.json({ limit: "100kb" }));
app.use(express.static(path.join(__dirname, "../public")));

app.use("/health", require("./routes/health"));
app.use("/auth", require("./routes/auth"));
app.use("/users", require("./routes/users"));
app.use("/orders", require("./routes/orders"));
app.use("/search", require("./routes/search"));
app.use("/upload", require("./routes/upload"));

app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: "Something went wrong" });
});

module.exports = app;
