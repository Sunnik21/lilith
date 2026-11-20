module.exports = {
  port: process.env.PORT || 3000,
  jwtSecret: process.env.JWT_SECRET || "taskly-super-secret-key",
  tokenTtl: "7d",
};
