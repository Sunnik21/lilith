const { PrismaClient } = require("@prisma/client");

const prisma = new PrismaClient({
  datasources: {
    db: { url: process.env.DATABASE_URL || "postgresql://taskly_admin:{{DB_PASSWORD}}@db.taskly-prod.internal:5432/taskly" },
  },
});

module.exports = prisma;
