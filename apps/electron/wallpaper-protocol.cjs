const fs = require("node:fs");
const path = require("node:path");
const { Readable } = require("node:stream");

const WALLPAPER_MIME_TYPES = {
  ".gif": "image/gif",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".mp4": "video/mp4",
  ".png": "image/png",
  ".webp": "image/webp"
};

function getWallpaperMimeType(filePath) {
  return WALLPAPER_MIME_TYPES[path.extname(filePath).toLowerCase()] || "application/octet-stream";
}

function parseWallpaperRange(rangeHeader, fileSize) {
  const value = String(rangeHeader || "").trim();
  if (!value) return null;
  const match = /^bytes=(\d*)-(\d*)$/i.exec(value);
  if (!match) return { invalid: true };

  const startValue = match[1];
  const endValue = match[2];
  if (!startValue && !endValue) return { invalid: true };

  let start;
  let end;
  if (!startValue) {
    const suffixLength = Number(endValue);
    if (!Number.isSafeInteger(suffixLength) || suffixLength <= 0) return { invalid: true };
    start = Math.max(0, fileSize - suffixLength);
    end = fileSize - 1;
  } else {
    start = Number(startValue);
    end = endValue ? Number(endValue) : fileSize - 1;
    if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start > end || start >= fileSize) {
      return { invalid: true };
    }
    end = Math.min(end, fileSize - 1);
  }
  return { start, end };
}

function createWallpaperFileResponse(request, target, stat) {
  const fileSize = Number(stat.size);
  const headers = new Headers({
    "Accept-Ranges": "bytes",
    "Cache-Control": "no-cache",
    "Content-Type": getWallpaperMimeType(target),
    "Last-Modified": stat.mtime.toUTCString()
  });
  const range = parseWallpaperRange(request.headers.get("range"), fileSize);
  if (range?.invalid) {
    headers.set("Content-Range", `bytes */${fileSize}`);
    headers.set("Content-Length", "0");
    return new Response(null, { status: 416, headers });
  }

  const isHead = request.method.toUpperCase() === "HEAD";
  const start = range?.start ?? 0;
  const end = range?.end ?? Math.max(0, fileSize - 1);
  const contentLength = Math.max(0, end - start + 1);
  headers.set("Content-Length", String(contentLength));
  if (range) headers.set("Content-Range", `bytes ${start}-${end}/${fileSize}`);

  if (isHead || contentLength === 0) {
    return new Response(null, { status: range ? 206 : 200, headers });
  }

  const stream = Readable.toWeb(fs.createReadStream(target, { start, end }));
  return new Response(stream, { status: range ? 206 : 200, headers });
}

module.exports = { createWallpaperFileResponse };
