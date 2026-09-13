const fs = require("node:fs");
const path = require("node:path");

const DEFAULT_SETUP = Object.freeze({
  language: 0,
  quality: 1,
  display: 0,
  width: 1280,
  height: 720,
  fullscreen: false
});

const STANDARD_RESOLUTIONS = Object.freeze([
  [854, 480],
  [960, 600],
  [1024, 576],
  [1136, 640],
  [1280, 720],
  [1280, 800],
  [1440, 900],
  [1536, 864],
  [1600, 900],
  [1680, 1050],
  [1920, 1080],
  [1920, 1200],
  [2048, 1152],
  [2560, 1440],
  [2560, 1600],
  [3200, 1800],
  [3840, 2160],
  [3840, 2400]
]);

function setupFilePath(gameDir) {
  const rawGameDir = String(gameDir || "").trim();
  if (!rawGameDir) {
    throw new Error("无效的 HS2 游戏目录。");
  }
  const normalizedGameDir = path.resolve(rawGameDir);
  if (!normalizedGameDir || normalizedGameDir === path.parse(normalizedGameDir).root) {
    throw new Error("无效的 HS2 游戏目录。");
  }
  return path.join(normalizedGameDir, "UserData", "setup.xml");
}

function decodeSetupText(buffer) {
  if (buffer.length >= 2 && buffer[0] === 0xff && buffer[1] === 0xfe) {
    return buffer.subarray(2).toString("utf16le");
  }
  if (buffer.length >= 2 && buffer[0] === 0xfe && buffer[1] === 0xff) {
    const littleEndian = Buffer.allocUnsafe(buffer.length - 2);
    for (let index = 2; index + 1 < buffer.length; index += 2) {
      littleEndian[index - 2] = buffer[index + 1];
      littleEndian[index - 1] = buffer[index];
    }
    return littleEndian.toString("utf16le");
  }
  return buffer.toString("utf8");
}

function encodeSetupText(text) {
  return Buffer.concat([Buffer.from([0xff, 0xfe]), Buffer.from(text, "utf16le")]);
}

function decodeXmlValue(value) {
  return String(value || "")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&amp;/g, "&");
}

function escapeXmlValue(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function readXmlField(xml, name) {
  const pattern = new RegExp(`<${name}\\b[^>]*>([\\s\\S]*?)</${name}>`, "i");
  const match = xml.match(pattern);
  return match ? decodeXmlValue(match[1].trim()) : "";
}

function parsePositiveInteger(value, fallback) {
  const parsed = Number.parseInt(String(value || ""), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function parseNonNegativeInteger(value, fallback) {
  const parsed = Number.parseInt(String(value || ""), 10);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}

function parseBoolean(value, fallback) {
  const normalized = String(value || "").trim().toLowerCase();
  if (["true", "1", "yes"].includes(normalized)) return true;
  if (["false", "0", "no"].includes(normalized)) return false;
  return fallback;
}

function parseResolution(value) {
  const match = String(value || "").match(/(\d+)\s*x\s*(\d+)/i);
  if (!match) return null;
  return {
    width: Number.parseInt(match[1], 10),
    height: Number.parseInt(match[2], 10)
  };
}

function formatResolution(width, height) {
  return `${width} x ${height}`;
}

function greatestCommonDivisor(left, right) {
  let a = Math.abs(left);
  let b = Math.abs(right);
  while (b) {
    const remainder = a % b;
    a = b;
    b = remainder;
  }
  return a || 1;
}

function formatSetupSize(width, height) {
  const divisor = greatestCommonDivisor(width, height);
  return `${formatResolution(width, height)} (${width / divisor} : ${height / divisor})`;
}

function normalizeSetup(input = {}) {
  const parsedSize = parseResolution(input.size);
  const width = parsePositiveInteger(input.width, parsedSize?.width || DEFAULT_SETUP.width);
  const height = parsePositiveInteger(input.height, parsedSize?.height || DEFAULT_SETUP.height);
  return {
    language: parseNonNegativeInteger(input.language, DEFAULT_SETUP.language),
    quality: Math.max(0, Math.min(2, parseNonNegativeInteger(input.quality, DEFAULT_SETUP.quality))),
    display: parseNonNegativeInteger(input.display, DEFAULT_SETUP.display),
    width,
    height,
    fullscreen: parseBoolean(input.fullscreen, DEFAULT_SETUP.fullscreen),
    resolution: formatResolution(width, height),
    size: formatSetupSize(width, height)
  };
}

function readGameSetup(gameDir) {
  const filePath = setupFilePath(gameDir);
  if (!fs.existsSync(filePath)) {
    return {
      exists: false,
      filePath,
      backupPath: "",
      setup: normalizeSetup(DEFAULT_SETUP)
    };
  }

  const xml = decodeSetupText(fs.readFileSync(filePath));
  if (!/<Setting\b[^>]*>/i.test(xml)) {
    throw new Error("setup.xml 缺少 Setting 节点，未读取配置。");
  }

  return {
    exists: true,
    filePath,
    backupPath: `${filePath}.bak`,
    setup: normalizeSetup({
      language: readXmlField(xml, "Language"),
      quality: readXmlField(xml, "Quality"),
      display: readXmlField(xml, "Display"),
      width: readXmlField(xml, "Width"),
      height: readXmlField(xml, "Height"),
      fullscreen: readXmlField(xml, "FullScreen"),
      size: readXmlField(xml, "Size")
    })
  };
}

function replaceOrInsertXmlField(xml, name, value) {
  const fieldPattern = new RegExp(`(<${name}\\b[^>]*>)[\\s\\S]*?(</${name}>)`, "i");
  if (fieldPattern.test(xml)) {
    return xml.replace(fieldPattern, (_match, opening, closing) => (
      `${opening}${escapeXmlValue(value)}${closing}`
    ));
  }

  const closingSetting = /<\/Setting\s*>/i;
  if (!closingSetting.test(xml)) {
    throw new Error("setup.xml 缺少 Setting 结束节点，未保存配置。");
  }
  return xml.replace(closingSetting, `  <${name}>${escapeXmlValue(value)}</${name}>\r\n</Setting>`);
}

function createSetupXml(setup) {
  return [
    '<?xml version="1.0" encoding="utf-16"?>',
    "<Setting>",
    `  <Size>${escapeXmlValue(setup.size)}</Size>`,
    `  <Width>${setup.width}</Width>`,
    `  <Height>${setup.height}</Height>`,
    `  <Quality>${setup.quality}</Quality>`,
    `  <FullScreen>${setup.fullscreen}</FullScreen>`,
    `  <Display>${setup.display}</Display>`,
    `  <Language>${setup.language}</Language>`,
    "</Setting>",
    ""
  ].join("\r\n");
}

function replaceSetupXml(xml, setup) {
  const fields = [
    ["Size", setup.size],
    ["Width", setup.width],
    ["Height", setup.height],
    ["Quality", setup.quality],
    ["FullScreen", setup.fullscreen],
    ["Display", setup.display],
    ["Language", setup.language]
  ];
  return fields.reduce((currentXml, [name, value]) => (
    replaceOrInsertXmlField(currentXml, name, value)
  ), xml);
}

function writeFileAtomically(filePath, data) {
  const temporaryPath = `${filePath}.star-manager-${process.pid}-${Date.now()}.tmp`;
  fs.writeFileSync(temporaryPath, data);
  try {
    try {
      fs.renameSync(temporaryPath, filePath);
    } catch (error) {
      if (!fs.existsSync(filePath)) throw error;
      fs.unlinkSync(filePath);
      fs.renameSync(temporaryPath, filePath);
    }
  } finally {
    if (fs.existsSync(temporaryPath)) fs.unlinkSync(temporaryPath);
  }
}

function writeGameSetup(gameDir, input) {
  const filePath = setupFilePath(gameDir);
  const setup = normalizeSetup(input);
  fs.mkdirSync(path.dirname(filePath), { recursive: true });

  let xml = createSetupXml(setup);
  if (fs.existsSync(filePath)) {
    xml = replaceSetupXml(decodeSetupText(fs.readFileSync(filePath)), setup);
    fs.copyFileSync(filePath, `${filePath}.bak`);
  }

  writeFileAtomically(filePath, encodeSetupText(xml));
  return {
    exists: true,
    filePath,
    backupPath: fs.existsSync(`${filePath}.bak`) ? `${filePath}.bak` : "",
    setup
  };
}

module.exports = {
  DEFAULT_SETUP,
  STANDARD_RESOLUTIONS,
  formatResolution,
  normalizeSetup,
  readGameSetup,
  setupFilePath,
  writeGameSetup
};
