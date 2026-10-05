const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { downloadRemoteCharacterCard, remoteCharacterFileName } = require("./remote-character-download.cjs");

const PNG_CONTENT = Buffer.concat([
  Buffer.from("89504e470d0a1a0a", "hex"),
  Buffer.from("sample AIS card content")
]);

test("downloads one fixed-host PNG into the chosen path", async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "star-manager-remote-card-"));
  try {
    const target = path.join(directory, "Sample_7.png");
    let requestedUrl = "";
    const result = await downloadRemoteCharacterCard(7, target, async (url, options) => {
      requestedUrl = url;
      assert.equal(options.redirect, "manual");
      return new Response(PNG_CONTENT, { status: 200, headers: { "content-type": "image/png" } });
    });

    assert.equal(requestedUrl, "https://db.bepis.moe/card/full/AI_000007.png");
    assert.equal(result.bytes, PNG_CONTENT.length);
    assert.deepEqual(await fs.readFile(target), PNG_CONTENT);
    assert.deepEqual(await fs.readdir(directory), ["Sample_7.png"]);
  } finally {
    await fs.rm(directory, { recursive: true, force: true });
  }
});

test("rejects non-PNG responses without creating a file", async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "star-manager-remote-card-"));
  try {
    const target = path.join(directory, "bad.png");
    await assert.rejects(
      downloadRemoteCharacterCard(7, target, async () => new Response("<html>blocked</html>", {
        status: 200,
        headers: { "content-type": "image/png" }
      })),
      /不是有效的 PNG/
    );
    assert.deepEqual(await fs.readdir(directory), []);
  } finally {
    await fs.rm(directory, { recursive: true, force: true });
  }
});

test("streams an AI scene PNG with a split signature to the chosen path", async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "star-manager-remote-scene-"));
  try {
    const target = path.join(directory, "Sample_AISCENE_26710.png");
    let requestedUrl = "";
    const result = await downloadRemoteCharacterCard(26710, target, async (url) => {
      requestedUrl = url;
      const body = new ReadableStream({
        start(controller) {
          controller.enqueue(PNG_CONTENT.subarray(0, 3));
          controller.enqueue(PNG_CONTENT.subarray(3));
          controller.close();
        }
      });
      return new Response(body, { status: 200, headers: { "content-type": "image/png" } });
    }, "AISCENE");

    assert.equal(requestedUrl, "https://db.bepis.moe/card/full/AISCENE_026710.png");
    assert.equal(result.bytes, PNG_CONTENT.length);
    assert.deepEqual(await fs.readFile(target), PNG_CONTENT);
    assert.deepEqual(await fs.readdir(directory), ["Sample_AISCENE_26710.png"]);
  } finally {
    await fs.rm(directory, { recursive: true, force: true });
  }
});

test("rejects scene files above the declared size limit before writing", async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "star-manager-remote-scene-"));
  try {
    const target = path.join(directory, "large.png");
    await assert.rejects(
      downloadRemoteCharacterCard(26710, target, async () => new Response(PNG_CONTENT, {
        status: 200,
        headers: { "content-type": "image/png", "content-length": String(513 * 1024 * 1024) }
      }), "AISCENE"),
      /512 MB 限制/
    );
    assert.deepEqual(await fs.readdir(directory), []);
  } finally {
    await fs.rm(directory, { recursive: true, force: true });
  }
});

test("sanitizes the suggested name and rejects invalid IDs", () => {
  assert.equal(remoteCharacterFileName(7, "A/B:*?"), "A_B____7.png");
  assert.equal(remoteCharacterFileName(26710, "Sample", "AISCENE"), "Sample_AISCENE_26710.png");
  assert.throws(() => remoteCharacterFileName(-1, "Sample"), /ID 无效/);
  assert.throws(() => remoteCharacterFileName(7, "Sample", "OTHER"), /类型无效/);
});
