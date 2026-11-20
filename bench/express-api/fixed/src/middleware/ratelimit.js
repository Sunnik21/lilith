const rateLimit = require("express-rate-limit");

// 10 attempts per 15 minutes per IP for login and signup
const authLimiter = rateLimit({ windowMs: 15 * 60 * 1000, limit: 10, standardHeaders: true, legacyHeaders: false });

module.exports = { authLimiter };
