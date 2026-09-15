const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const remoteIndexPath = path.join(
  root,
  "backend",
  "runtime",
  "remote",
  "remote_zipmod_index.sqlite"
);

if (!fs.existsSync(remoteIndexPath) || !fs.statSync(remoteIndexPath).isFile()) {
  console.error(`Required remote mod database is missing: ${remoteIndexPath}`);
  console.error("Build or place the remote index before running npm run package:win.");
  process.exit(1);
}

console.log(`Package input found: ${remoteIndexPath}`);
