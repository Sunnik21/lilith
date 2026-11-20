const { PrismaClient } = require("@prisma/client");

// DATABASE_URL comes from the environment only.
const prisma = new PrismaClient();

module.exports = prisma;
