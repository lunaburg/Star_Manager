const fs = require("node:fs");
const path = require("node:path");

const appRoot = path.resolve(__dirname, "..");
const releaseRoot = path.resolve(appRoot, "release", "win-unpacked");
const runtimeRoot = path.join(releaseRoot, "runtime");
const sourceRemoteRoot = path.join(appRoot, "backend", "runtime", "remote");
const targetRemoteRoot = path.join(runtimeRoot, "remote");
const remoteIndexName = "remote_zipmod_index.sqlite";

if (!fs.existsSync(releaseRoot) || !fs.statSync(releaseRoot).isDirectory()) {
  console.error(`Packaged app directory is missing: ${releaseRoot}`);
  process.exit(1);
}

const remoteIndexSource = path.join(sourceRemoteRoot, remoteIndexName);
const remoteIndexTarget = path.join(targetRemoteRoot, remoteIndexName);
if (!fs.existsSync(remoteIndexSource) || !fs.statSync(remoteIndexSource).isFile()) {
  console.error(`Required remote mod database is missing: ${remoteIndexSource}`);
  process.exit(1);
}

// The release runtime directory is a packaging output, not a user data directory.
// Reset it completely so local databases, settings, caches, trash, and previews
// from a previous launch can never leak into the next published package.
fs.rmSync(runtimeRoot, { recursive: true, force: true });
fs.mkdirSync(runtimeRoot, { recursive: true });
fs.cpSync(sourceRemoteRoot, targetRemoteRoot, { recursive: true });

if (!fs.existsSync(remoteIndexTarget) || !fs.statSync(remoteIndexTarget).isFile()) {
  console.error(`Failed to stage remote mod database: ${remoteIndexTarget}`);
  process.exit(1);
}

console.log(`Reset packaged runtime: ${runtimeRoot}`);
console.log(`Preserved remote mod index: ${remoteIndexTarget}`);
