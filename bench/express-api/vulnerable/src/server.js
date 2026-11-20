const app = require("./app");
const config = require("./config");

app.listen(config.port, () => {
  process.stdout.write(`API listening on ${config.port}\n`);
});
