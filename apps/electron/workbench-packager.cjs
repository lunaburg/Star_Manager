const fs = require("node:fs");
const path = require("node:path");
const zlib = require("node:zlib");

const ZIP_LOCAL_FILE_SIGNATURE = 0x04034b50;
const ZIP_CENTRAL_FILE_SIGNATURE = 0x02014b50;
const ZIP_END_SIGNATURE = 0x06054b50;
const ZIP_UTF8_FLAG = 0x0800;
const ZIP_DEFLATED = 8;
const ZIP_STORED = 0;

const CRC32_TABLE = (() => {
  const table = [];
  for (let index = 0; index < 256; index += 1) {
    let value = index;
    for (let bit = 0; bit < 8; bit += 1) {
      value = (value & 1) ? (0xedb88320 ^ (value >>> 1)) : (value >>> 1);
    }
    table.push(value >>> 0);
  }
  return table;
})();

function crc32(buffer) {
  let value = 0xffffffff;
  for (const byte of buffer) {
    value = CRC32_TABLE[(value ^ byte) & 0xff] ^ (value >>> 8);
  }
  return (value ^ 0xffffffff) >>> 0;
}

function isPathInside(parentPath, childPath) {
  const relativePath = path.relative(parentPath, childPath);
  return Boolean(relativePath) && !relativePath.startsWith("..") && !path.isAbsolute(relativePath);
}

function normalizeArchivePath(filePath) {
  return String(filePath || "").replaceAll(path.sep, "/").replaceAll("\\", "/");
}

function safeFilePart(value, fallback) {
  const cleaned = String(value || "")
    .trim()
    .replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_")
    .replace(/[. ]+$/g, "")
    .trim();
  return cleaned || fallback;
}

function parseCsvRows(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (quoted) {
      if (character === '"' && text[index + 1] === '"') {
        cell += '"';
        index += 1;
      } else if (character === '"') {
        quoted = false;
      } else {
        cell += character;
      }
      continue;
    }

    if (character === '"' && cell.length === 0) {
      quoted = true;
    } else if (character === ",") {
      row.push(cell);
      cell = "";
    } else if (character === "\n") {
      row.push(cell.replace(/\r$/, ""));
      if (row.some((value) => value.trim())) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += character;
    }
  }

  if (cell.length || row.length) {
    row.push(cell.replace(/\r$/, ""));
    if (row.some((value) => value.trim())) rows.push(row);
  }
  return rows;
}

function collectFiles(directoryPath, predicate, files = []) {
  if (!fs.existsSync(directoryPath) || !fs.statSync(directoryPath).isDirectory()) return files;
  for (const entry of fs.readdirSync(directoryPath, { withFileTypes: true })) {
    const entryPath = path.join(directoryPath, entry.name);
    if (entry.isDirectory()) {
      collectFiles(entryPath, predicate, files);
    } else if (entry.isFile() && predicate(entryPath)) {
      files.push(entryPath);
    }
  }
  return files;
}

function assertRegularProjectFile(projectPath, filePath, description) {
  const resolvedProjectPath = path.resolve(projectPath);
  const resolvedFilePath = path.resolve(filePath);
  if (!isPathInside(resolvedProjectPath, resolvedFilePath)) {
    throw new Error(`${description}必须位于工程目录内`);
  }
  const stat = fs.lstatSync(resolvedFilePath);
  if (!stat.isFile() || stat.isSymbolicLink()) {
    throw new Error(`${description}不是普通文件`);
  }
  return resolvedFilePath;
}

const THUMBNAIL_IMAGE_EXTENSIONS = new Set([".png", ".jpg", ".jpeg", ".tga", ".webp"]);

function normalizeProjectReference(value, description = "资源") {
  const raw = String(value || "").trim().replaceAll("\\", "/");
  if (!raw) return "";
  if (path.posix.isAbsolute(raw) || path.win32.isAbsolute(raw) || /^[a-zA-Z]:/.test(raw)) {
    throw new Error(`${description}引用路径不能是绝对路径：${raw}`);
  }

  let normalized = path.posix.normalize(raw).replace(/^\.\//, "");
  if (normalized.toLocaleLowerCase().startsWith("abdata/")) {
    normalized = normalized.slice("abdata/".length);
  }
  if (!normalized || normalized === "." || normalized.startsWith("../") || normalized === "..") {
    throw new Error(`${description}引用路径无效：${raw}`);
  }
  return normalized;
}

function normalizeUnity3dReference(value) {
  const raw = String(value || "").trim().replaceAll("\\", "/");
  const normalized = normalizeProjectReference(raw, "Unity3D");
  if (path.posix.extname(normalized).toLocaleLowerCase() !== ".unity3d") {
    throw new Error(`Unity3D 引用路径必须指向 .unity3d：${raw}`);
  }
  return normalized;
}

function isThumbnailImageReference(reference) {
  return THUMBNAIL_IMAGE_EXTENSIONS.has(path.posix.extname(reference).toLocaleLowerCase());
}

function collectThumbnailFileCandidates(thumbReference, thumbTexture) {
  const candidates = [];
  const seen = new Set();
  const addCandidate = (value) => {
    const normalized = normalizeProjectReference(value, "缩略图");
    const key = normalized.toLocaleLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      candidates.push(normalized);
    }
  };

  if (isThumbnailImageReference(thumbReference)) addCandidate(thumbReference);
  const texture = String(thumbTexture || "").trim().replaceAll("\\", "/");
  if (!texture) return candidates;

  const normalizedTexture = normalizeProjectReference(texture, "缩略图");
  const bases = [thumbReference];
  if (path.posix.extname(thumbReference).toLocaleLowerCase() === ".unity3d") {
    bases.push(thumbReference.slice(0, -".unity3d".length));
  }
  for (const base of bases) {
    const candidate = path.posix.join(base, normalizedTexture);
    addCandidate(candidate);
    if (!isThumbnailImageReference(normalizedTexture)) {
      for (const extension of THUMBNAIL_IMAGE_EXTENSIONS) {
        addCandidate(`${candidate}${extension}`);
      }
    }
  }
  return candidates;
}

function addArchiveFile(archiveFiles, seenNames, sourcePath, archivePath, projectPath, description) {
  const normalizedArchivePath = normalizeArchivePath(archivePath);
  const key = normalizedArchivePath.toLocaleLowerCase();
  if (seenNames.has(key)) return;
  const safeSourcePath = assertRegularProjectFile(projectPath, sourcePath, description);
  seenNames.add(key);
  archiveFiles.push({ sourcePath: safeSourcePath, archivePath: normalizedArchivePath });
}

function rememberResourceReference(resourceReferences, reference) {
  const key = reference.toLocaleLowerCase();
  if (!resourceReferences.has(key)) resourceReferences.set(key, reference);
}

function collectPackageFiles(projectPath, project, onProgress) {
  const archiveFiles = [];
  const seenNames = new Set();
  const manifestPath = assertRegularProjectFile(projectPath, path.join(projectPath, "manifest.xml"), "manifest.xml");
  addArchiveFile(archiveFiles, seenNames, manifestPath, "manifest.xml", projectPath, "manifest.xml");

  const listRoot = path.join(projectPath, "abdata", "list");
  onProgress?.({ stage: "scanning", message: "正在读取工程 CSV" });
  const csvFiles = collectFiles(
    listRoot,
    (filePath) => path.extname(filePath).toLocaleLowerCase() === ".csv"
  ).sort((left, right) => left.localeCompare(right, "en"));
  if (!csvFiles.length) {
    throw new Error("工程中没有可打包的 abdata/list CSV 文件");
  }

  const resourceReferences = new Map();
  const thumbnailReferences = [];
  for (const csvPath of csvFiles) {
    const relativeCsvPath = normalizeArchivePath(path.relative(projectPath, csvPath));
    const rows = parseCsvRows(fs.readFileSync(csvPath, "utf-8").replace(/^\uFEFF/, ""));
    const headerIndex = rows.findIndex((row) => {
      const columns = new Set(row.map((value) => value.trim()));
      return columns.has("ID") && columns.has("Name");
    });
    if (headerIndex < 0) {
      throw new Error(`CSV 表头无效：${relativeCsvPath}`);
    }

    const header = rows[headerIndex].map((value) => value.trim());
    const mainAbIndex = header.indexOf("MainAB");
    const thumbAbIndex = header.indexOf("ThumbAB");
    const thumbTexIndex = header.indexOf("ThumbTex");
    for (const row of rows.slice(headerIndex + 1)) {
      if (!row.some((value) => value.trim())) continue;
      if (mainAbIndex >= 0) {
        const rawMainReference = String(row[mainAbIndex] || "").trim();
        if (rawMainReference && rawMainReference !== "0") {
          const reference = normalizeUnity3dReference(rawMainReference);
          rememberResourceReference(resourceReferences, reference);
        }
      }
      if (thumbAbIndex >= 0) {
        const rawThumbReference = String(row[thumbAbIndex] || "").trim();
        if (rawThumbReference && rawThumbReference !== "0") {
          thumbnailReferences.push({
            reference: normalizeProjectReference(rawThumbReference, "缩略图"),
            texture: thumbTexIndex >= 0 ? String(row[thumbTexIndex] || "").trim() : ""
          });
        }
      }
    }
    addArchiveFile(archiveFiles, seenNames, csvPath, relativeCsvPath, projectPath, `CSV 文件 ${relativeCsvPath}`);
  }

  const abdataRoot = path.join(projectPath, "abdata");
  onProgress?.({ stage: "scanning", message: "正在定位 CSV 引用的 Unity3D" });

  for (const reference of [...resourceReferences.values()].sort()) {
    const sourcePath = path.join(abdataRoot, ...reference.split("/"));
    if (!fs.existsSync(sourcePath) || !fs.statSync(sourcePath).isFile()) {
      throw new Error(`CSV 引用的 Unity3D 文件不存在：abdata/${reference}`);
    }
    addArchiveFile(
      archiveFiles,
      seenNames,
      sourcePath,
      `abdata/${reference}`,
      projectPath,
      `Unity3D 文件 abdata/${reference}`
    );
  }

  for (const { reference, texture } of thumbnailReferences) {
    if (path.posix.extname(reference).toLocaleLowerCase() === ".unity3d") {
      rememberResourceReference(resourceReferences, reference);
      continue;
    }

    const directSourcePath = path.join(abdataRoot, ...reference.split("/"));
    if (fs.existsSync(directSourcePath) && fs.statSync(directSourcePath).isFile()) {
      addArchiveFile(
        archiveFiles,
        seenNames,
        directSourcePath,
        `abdata/${reference}`,
        projectPath,
        `缩略图文件 abdata/${reference}`
      );
      continue;
    }

    for (const candidate of collectThumbnailFileCandidates(reference, texture)) {
      const sourcePath = path.join(abdataRoot, ...candidate.split("/"));
      if (!fs.existsSync(sourcePath) || !fs.statSync(sourcePath).isFile()) continue;
      addArchiveFile(
        archiveFiles,
        seenNames,
        sourcePath,
        `abdata/${candidate}`,
        projectPath,
        `缩略图文件 abdata/${candidate}`
      );
      break;
    }
  }

  for (const reference of [...resourceReferences.values()].sort()) {
    if (archiveFiles.some((file) => file.archivePath.toLocaleLowerCase() === `abdata/${reference}`)) continue;
    const sourcePath = path.join(abdataRoot, ...reference.split("/"));
    if (!fs.existsSync(sourcePath) || !fs.statSync(sourcePath).isFile()) {
      throw new Error(`CSV 引用的 Unity3D 文件不存在：abdata/${reference}`);
    }
    addArchiveFile(
      archiveFiles,
      seenNames,
      sourcePath,
      `abdata/${reference}`,
      projectPath,
      `Unity3D 文件 abdata/${reference}`
    );
  }

  return archiveFiles;
}

function zipDateTime(date = new Date()) {
  const year = Math.max(1980, Math.min(2107, date.getFullYear()));
  return {
    time: (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2),
    date: ((year - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate()
  };
}

function createZipArchive(archiveFiles, outputPath, onProgress) {
  const centralChunks = [];
  let localOffset = 0;
  const fileHandle = fs.openSync(outputPath, "w");

  try {
    for (let index = 0; index < archiveFiles.length; index += 1) {
      const file = archiveFiles[index];
      const data = fs.readFileSync(file.sourcePath);
      const method = path.extname(file.sourcePath).toLocaleLowerCase() === ".unity3d"
        ? ZIP_STORED
        : ZIP_DEFLATED;
      const compressed = method === ZIP_STORED
        ? data
        : zlib.deflateRawSync(data, { level: 6 });
      const name = Buffer.from(file.archivePath, "utf8");
      const { time, date } = zipDateTime(fs.statSync(file.sourcePath).mtime);
      const checksum = crc32(data);

      if (compressed.length > 0xffffffff || data.length > 0xffffffff || localOffset > 0xffffffff) {
        throw new Error(`文件过大，无法生成标准 zipmod：${file.archivePath}`);
      }

      const localHeader = Buffer.alloc(30 + name.length);
      localHeader.writeUInt32LE(ZIP_LOCAL_FILE_SIGNATURE, 0);
      localHeader.writeUInt16LE(20, 4);
      localHeader.writeUInt16LE(ZIP_UTF8_FLAG, 6);
      localHeader.writeUInt16LE(method, 8);
      localHeader.writeUInt16LE(time, 10);
      localHeader.writeUInt16LE(date, 12);
      localHeader.writeUInt32LE(checksum, 14);
      localHeader.writeUInt32LE(compressed.length, 18);
      localHeader.writeUInt32LE(data.length, 22);
      localHeader.writeUInt16LE(name.length, 26);
      name.copy(localHeader, 30);
      fs.writeSync(fileHandle, localHeader);
      fs.writeSync(fileHandle, compressed);

      const centralHeader = Buffer.alloc(46 + name.length);
      centralHeader.writeUInt32LE(ZIP_CENTRAL_FILE_SIGNATURE, 0);
      centralHeader.writeUInt16LE(20, 4);
      centralHeader.writeUInt16LE(20, 6);
      centralHeader.writeUInt16LE(ZIP_UTF8_FLAG, 8);
      centralHeader.writeUInt16LE(method, 10);
      centralHeader.writeUInt16LE(time, 12);
      centralHeader.writeUInt16LE(date, 14);
      centralHeader.writeUInt32LE(checksum, 16);
      centralHeader.writeUInt32LE(compressed.length, 20);
      centralHeader.writeUInt32LE(data.length, 24);
      centralHeader.writeUInt16LE(name.length, 28);
      centralHeader.writeUInt32LE(0, 38);
      centralHeader.writeUInt32LE(localOffset, 42);
      name.copy(centralHeader, 46);
      centralChunks.push(centralHeader);

      localOffset += localHeader.length + compressed.length;
      onProgress?.({
        stage: "compressing",
        current: index + 1,
        total: archiveFiles.length,
        fileName: file.archivePath,
        fileBytes: data.length
      });
    }

    const centralDirectory = Buffer.concat(centralChunks);
    const endRecord = Buffer.alloc(22);
    endRecord.writeUInt32LE(ZIP_END_SIGNATURE, 0);
    endRecord.writeUInt16LE(archiveFiles.length, 8);
    endRecord.writeUInt16LE(archiveFiles.length, 10);
    endRecord.writeUInt32LE(centralDirectory.length, 12);
    endRecord.writeUInt32LE(localOffset, 16);
    fs.writeSync(fileHandle, centralDirectory);
    fs.writeSync(fileHandle, endRecord);
  } finally {
    fs.closeSync(fileHandle);
  }
}

function nextAvailableTarget(modsPath, baseName, reservedPaths) {
  const reserved = new Set(reservedPaths.map((filePath) => path.resolve(filePath).toLocaleLowerCase()));
  let suffix = 0;
  while (true) {
    const name = suffix ? `${baseName}_${suffix}.zipmod` : `${baseName}.zipmod`;
    const candidate = path.resolve(modsPath, name);
    if (!fs.existsSync(candidate) || reserved.has(candidate.toLocaleLowerCase())) return candidate;
    suffix += 1;
  }
}

function packageWorkbenchMod({ projectPath, gameDir, project, oldZipmodPaths = [], onProgress }) {
  const resolvedProjectPath = path.resolve(String(projectPath || ""));
  const resolvedGameDir = path.resolve(String(gameDir || ""));
  if (!fs.existsSync(resolvedGameDir) || !fs.statSync(resolvedGameDir).isDirectory()) {
    throw new Error("游戏目录不存在，请先选择有效的 HS2 游戏目录");
  }
  if (!fs.existsSync(path.join(resolvedGameDir, "HoneySelect2.exe"))) {
    throw new Error("所选目录不是有效的 HS2 游戏目录");
  }
  if (!project?.guid || !project?.name || !project?.author) {
    throw new Error("工程 manifest.xml 信息不完整");
  }

  const archiveFiles = collectPackageFiles(resolvedProjectPath, project, onProgress);
  const modsPath = path.join(resolvedGameDir, "mods");
  fs.mkdirSync(modsPath, { recursive: true });

  const baseName = `[${safeFilePart(project.author, "author")}]_${safeFilePart(project.name, "mod")}`;
  onProgress?.({ stage: "scanning", message: "正在使用模组数据库定位旧版本" });
  const resolvedModsPath = path.resolve(modsPath);
  const oldZipmods = (Array.isArray(oldZipmodPaths) ? oldZipmodPaths : [])
    .map((filePath) => path.resolve(String(filePath || "")))
    .filter((filePath, index, paths) => (
      paths.indexOf(filePath) === index
      && path.extname(filePath).toLocaleLowerCase() === ".zipmod"
      && isPathInside(resolvedModsPath, filePath)
      && fs.existsSync(filePath)
      && fs.statSync(filePath).isFile()
    ));
  const targetPath = nextAvailableTarget(modsPath, baseName, oldZipmods);
  const temporaryPath = path.join(
    modsPath,
    `.${path.basename(targetPath)}.${process.pid}.${Date.now()}.tmp`
  );

  try {
    onProgress?.({ stage: "compressing", current: 0, total: archiveFiles.length, message: "正在写入 zipmod" });
    createZipArchive(archiveFiles, temporaryPath, onProgress);
    for (const oldPath of oldZipmods) {
      if (fs.existsSync(oldPath)) fs.rmSync(oldPath, { force: false });
    }
    fs.renameSync(temporaryPath, targetPath);
  } catch (error) {
    fs.rmSync(temporaryPath, { force: true });
    throw error;
  }

  return {
    ok: true,
    gameDir: resolvedGameDir,
    modsDir: modsPath,
    zipmodPath: targetPath,
    fileName: path.basename(targetPath),
    fileCount: archiveFiles.length,
    files: archiveFiles.map((file) => file.archivePath),
    replacedCount: oldZipmods.length
  };
}

module.exports = { packageWorkbenchMod };
