const crypto = require("node:crypto");
const fs = require("node:fs/promises");
const path = require("node:path");

const PNG_SIGNATURE = Buffer.from("89504e470d0a1a0a", "hex");
const CARD_OPTIONS = {
  AI: { maxBytes: 64 * 1024 * 1024, timeoutMs: 30000 },
  AISCENE: { maxBytes: 512 * 1024 * 1024, timeoutMs: 10 * 60 * 1000 }
};

function validateCardType(cardType) {
  if (!Object.hasOwn(CARD_OPTIONS, cardType)) throw new Error("网站卡片类型无效");
  return cardType;
}

function validateCardId(cardId) {
  if (!Number.isSafeInteger(cardId) || cardId <= 0) {
    throw new Error("卡片 ID 无效");
  }
  return cardId;
}

function remoteCharacterFileName(cardId, name, cardType = "AI") {
  const id = validateCardId(cardId);
  const type = validateCardType(cardType);
  const safeName = String(name || "")
    .replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_")
    .replace(/[. ]+$/g, "")
    .trim()
    .slice(0, 80);
  return type === "AISCENE"
    ? `${safeName || "Scene"}_AISCENE_${id}.png`
    : `${safeName || "AI"}_${id}.png`;
}

async function downloadRemoteCharacterCard(cardId, destinationPath, fetchRemote, cardType = "AI") {
  const id = validateCardId(cardId);
  const type = validateCardType(cardType);
  const options = CARD_OPTIONS[type];
  if (typeof destinationPath !== "string" || !destinationPath.trim()) {
    throw new Error("请选择卡片保存位置");
  }
  const targetPath = path.resolve(destinationPath);
  if (path.extname(targetPath).toLowerCase() !== ".png") {
    throw new Error("卡片必须保存为 PNG 文件");
  }
  const sourceUrl = `https://db.bepis.moe/card/full/${type}_${String(id).padStart(6, "0")}.png`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeoutMs);
  const temporaryPath = path.join(
    path.dirname(targetPath),
    `.${path.basename(targetPath)}.${process.pid}.${crypto.randomBytes(6).toString("hex")}.part`
  );
  let fileHandle;
  try {
    const response = await fetchRemote(sourceUrl, {
      redirect: "manual",
      headers: { Accept: "image/png" },
      signal: controller.signal
    });
    if (response.status !== 200 || (response.url && response.url !== sourceUrl)) {
      throw new Error(`卡片下载失败（HTTP ${response.status}）`);
    }
    if (!/^image\/png(?:;|$)/i.test(response.headers.get("content-type") || "")) {
      throw new Error("网站未返回 PNG 卡片");
    }
    const reportedSize = Number(response.headers.get("content-length") || 0);
    if (reportedSize > options.maxBytes) {
      throw new Error(`卡片文件超过 ${options.maxBytes / (1024 * 1024)} MB 限制`);
    }
    if (!response.body) {
      throw new Error("卡片下载没有文件内容");
    }
    const reader = response.body.getReader();
    const signature = Buffer.alloc(PNG_SIGNATURE.length);
    let signatureBytes = 0;
    let totalBytes = 0;
    fileHandle = await fs.open(temporaryPath, "wx");
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = Buffer.from(value);
      totalBytes += chunk.length;
      if (totalBytes > options.maxBytes) {
        throw new Error(`卡片文件超过 ${options.maxBytes / (1024 * 1024)} MB 限制`);
      }
      if (signatureBytes < PNG_SIGNATURE.length) {
        const remaining = Math.min(PNG_SIGNATURE.length - signatureBytes, chunk.length);
        chunk.copy(signature, signatureBytes, 0, remaining);
        signatureBytes += remaining;
        if (signatureBytes === PNG_SIGNATURE.length && !signature.equals(PNG_SIGNATURE)) {
          throw new Error("下载内容不是有效的 PNG 卡片");
        }
      }
      let offset = 0;
      while (offset < chunk.length) {
        const { bytesWritten } = await fileHandle.write(chunk, offset, chunk.length - offset);
        if (bytesWritten <= 0) throw new Error("卡片文件写入失败");
        offset += bytesWritten;
      }
    }
    if (signatureBytes < PNG_SIGNATURE.length) {
      throw new Error("下载内容不是有效的 PNG 卡片");
    }
    await fileHandle.close();
    fileHandle = null;
    await fs.rename(temporaryPath, targetPath);
    return { ok: true, path: targetPath, bytes: totalBytes };
  } finally {
    clearTimeout(timeout);
    controller.abort();
    if (fileHandle) await fileHandle.close().catch(() => {});
    await fs.rm(temporaryPath, { force: true });
  }
}

module.exports = { downloadRemoteCharacterCard, remoteCharacterFileName };
