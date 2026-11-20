if (!process.env.JWT_SECRET || process.env.JWT_SECRET.length < 32) {
  throw new Error("JWT_SECRET must be set (32+ random characters)");
}

module.exports = {
  port: process.env.PORT || 3000,
  jwtSecret: process.env.JWT_SECRET,
  tokenTtl: "7d",
  allowedOrigins: (process.env.ALLOWED_ORIGINS || "https://taskly.shop").split(","),
};
