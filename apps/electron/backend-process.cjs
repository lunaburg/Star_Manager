const { execFile } = require("node:child_process");

function processHasExited(child) {
  return child.exitCode !== null || child.signalCode !== null;
}

function waitForProcessExit(child, timeoutMs) {
  if (!child || processHasExited(child)) {
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      child.removeListener("exit", finish);
      child.removeListener("close", finish);
      resolve();
    };

    const timeout = setTimeout(finish, timeoutMs);
    child.once("exit", finish);
    child.once("close", finish);
  });
}

function runTaskkill(execFileImpl, pid) {
  return new Promise((resolve, reject) => {
    execFileImpl(
      "taskkill.exe",
      ["/PID", String(pid), "/T", "/F"],
      { windowsHide: true },
      (error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve();
      }
    );
  });
}

async function terminateProcessTree(
  child,
  { platform = process.platform, timeoutMs = 5000, execFileImpl = execFile } = {}
) {
  if (!child || processHasExited(child)) {
    return;
  }

  const exitPromise = waitForProcessExit(child, timeoutMs);
  if (platform === "win32" && child.pid) {
    try {
      await runTaskkill(execFileImpl, child.pid);
    } catch {
      // The process may have exited between the check and taskkill. The exit
      // wait below still gives the child a chance to report its final state.
    }
  } else {
    try {
      child.kill("SIGTERM");
    } catch {
      // The process may have exited between the check and kill.
    }
  }

  await exitPromise;
}

module.exports = {
  processHasExited,
  terminateProcessTree
};
