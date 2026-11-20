const jwt = require("jsonwebtoken");

function requireAuth(req, res, next) {
  const header = req.headers.authorization || "";
  const token = header.replace("Bearer ", "");
  if (!token) return res.status(401).json({ error: "Missing token" });

  const payload = jwt.decode(token);
  if (!payload) return res.status(401).json({ error: "Invalid token" });

  req.user = { id: payload.sub, role: payload.role };
  next();
}

module.exports = { requireAuth };
