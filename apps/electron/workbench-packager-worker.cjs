const { parentPort, workerData } = require("node:worker_threads");
const { packageWorkbenchMod } = require("./workbench-packager.cjs");

try {
  const result = packageWorkbenchMod({
    ...workerData,
    onProgress: (progress) => parentPort.postMessage({ type: "progress", progress })
  });
  parentPort.postMessage({ type: "result", result });
} catch (error) {
  parentPort.postMessage({
    type: "result",
    result: {
      ok: false,
      error: error?.message || String(error)
    }
  });
}
