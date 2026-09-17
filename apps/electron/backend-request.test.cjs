const test = require("node:test");
const assert = require("node:assert/strict");

const { fetchBackendRequest } = require("./backend-request.cjs");

test("retries a failed GET request", async () => {
  let calls = 0;
  const result = await fetchBackendRequest("http://127.0.0.1:8765/trash", { method: "GET" }, {
    fetchImpl: async () => {
      calls += 1;
      if (calls === 1) throw new Error("temporary network failure");
      return { json: async () => ({ ok: true }) };
    },
    sleepImpl: async () => {}
  });

  assert.equal(calls, 2);
  assert.deepEqual(result, { ok: true });
});

test("does not retry a failed restore mutation", async () => {
  let calls = 0;
  const result = await fetchBackendRequest("http://127.0.0.1:8765/trash/mods/entry/restore", { method: "POST" }, {
    fetchImpl: async () => {
      calls += 1;
      throw new Error("response connection closed");
    }
  });

  assert.equal(calls, 1);
  assert.equal(result.ok, false);
  assert.match(result.error, /response connection closed/);
});
