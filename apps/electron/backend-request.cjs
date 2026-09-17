const RETRYABLE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const MAX_RETRY_ATTEMPTS = 20;

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function fetchBackendRequest(url, options = {}, dependencies = {}) {
  const method = String(options.method || "GET").toUpperCase();
  const fetchImpl = dependencies.fetchImpl || globalThis.fetch;
  const sleepImpl = dependencies.sleepImpl || sleep;
  const attempts = RETRYABLE_METHODS.has(method) ? MAX_RETRY_ATTEMPTS : 1;
  let lastError;

  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      const response = await fetchImpl(url, options);
      return response.json();
    } catch (error) {
      lastError = error;
      if (attempt + 1 < attempts) await sleepImpl(250);
    }
  }

  return {
    ok: false,
    error: `Python backend unavailable: ${lastError ? lastError.message : "unknown error"}`
  };
}

module.exports = { fetchBackendRequest };
