const express = require("express");
const cors = require("cors");
const path = require("path");

const app = express();

app.use(cors({ origin: true, credentials: true }));
app.use(express.json());
app.use(express.static(path.join(__dirname, "../public")));

app.use("/health", require("./routes/health"));
app.use("/auth", require("./routes/auth"));
app.use("/users", require("./routes/users"));
app.use("/orders", require("./routes/orders"));
app.use("/search", require("./routes/search"));
app.use("/upload", require("./routes/upload"));
app.use("/admin", require("./routes/admin"));

app.use((err, req, res, next) => {
  res.status(500).json({ error: err.message, stack: err.stack });
});

module.exports = app;
