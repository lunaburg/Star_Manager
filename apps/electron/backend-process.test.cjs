const assert = require("node:assert/strict");
const { EventEmitter } = require("node:events");
const test = require("node:test");

const { terminateProcessTree } = require("./backend-process.cjs");

test("Windows backend shutdown terminates the complete process tree", async () => {
  const child = new EventEmitter();
  child.pid = 12345;
  child.exitCode = null;
  child.signalCode = null;

  let command;
  const shutdown = terminateProcessTree(child, {
    platform: "win32",
    execFileImpl: (file, args, options, callback) => {
      command = { file, args, options };
      setImmediate(() => {
        child.exitCode = 0;
        child.emit("exit", 0, null);
        callback(null, "", "");
      });
    }
  });

  await shutdown;

  assert.deepEqual(command, {
    file: "taskkill.exe",
    args: ["/PID", "12345", "/T", "/F"],
    options: { windowsHide: true }
  });
});

test("non-Windows backend shutdown sends SIGTERM to the child", async () => {
  const child = new EventEmitter();
  child.pid = 12345;
  child.exitCode = null;
  child.signalCode = null;
  let signal;
  child.kill = (value) => {
    signal = value;
    child.signalCode = value;
    child.emit("exit", null, value);
    return true;
  };

  await terminateProcessTree(child, { platform: "linux" });

  assert.equal(signal, "SIGTERM");
});
