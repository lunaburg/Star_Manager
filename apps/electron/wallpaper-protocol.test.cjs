const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { after, test } = require("node:test");
const { createWallpaperFileResponse } = require("./wallpaper-protocol.cjs");

const tempDirectory = fs.mkdtempSync(path.join(os.tmpdir(), "star-manager-wallpaper-"));
const videoPath = path.join(tempDirectory, "sample.mp4");
const videoBytes = Buffer.from("0123456789abcdefghijklmnopqrstuvwxyz", "ascii");
fs.writeFileSync(videoPath, videoBytes);
const videoStat = fs.statSync(videoPath);

after(() => {
  fs.rmSync(tempDirectory, { recursive: true, force: true });
});

function request(method = "GET", range = "") {
  return new Request("wallpaper://file", {
    method,
    headers: range ? { Range: range } : undefined
  });
}

test("serves full wallpaper files with a media type and range support", async () => {
  const response = createWallpaperFileResponse(request(), videoPath, videoStat);

  assert.equal(response.status, 200);
  assert.equal(response.headers.get("accept-ranges"), "bytes");
  assert.equal(response.headers.get("content-type"), "video/mp4");
  assert.equal(response.headers.get("content-length"), String(videoBytes.length));
  assert.deepEqual(Buffer.from(await response.arrayBuffer()), videoBytes);
});

test("serves byte ranges for MP4 seeking and loop reloads", async () => {
  const response = createWallpaperFileResponse(request("GET", "bytes=7-13"), videoPath, videoStat);

  assert.equal(response.status, 206);
  assert.equal(response.headers.get("content-range"), `bytes 7-13/${videoBytes.length}`);
  assert.equal(response.headers.get("content-length"), "7");
  assert.deepEqual(Buffer.from(await response.arrayBuffer()), videoBytes.subarray(7, 14));
});

test("supports suffix ranges and HEAD requests", async () => {
  const suffixResponse = createWallpaperFileResponse(request("GET", "bytes=-5"), videoPath, videoStat);
  assert.equal(suffixResponse.status, 206);
  assert.equal(suffixResponse.headers.get("content-range"), `bytes ${videoBytes.length - 5}-${videoBytes.length - 1}/${videoBytes.length}`);
  assert.deepEqual(Buffer.from(await suffixResponse.arrayBuffer()), videoBytes.subarray(-5));

  const headResponse = createWallpaperFileResponse(request("HEAD"), videoPath, videoStat);
  assert.equal(headResponse.status, 200);
  assert.equal(headResponse.headers.get("content-length"), String(videoBytes.length));
  assert.equal(headResponse.body, null);
});

test("returns 416 for an unsatisfiable range", () => {
  const response = createWallpaperFileResponse(request("GET", `bytes=${videoBytes.length}-`), videoPath, videoStat);

  assert.equal(response.status, 416);
  assert.equal(response.headers.get("content-range"), `bytes */${videoBytes.length}`);
  assert.equal(response.headers.get("content-length"), "0");
});
