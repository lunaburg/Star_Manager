const rendererBootStart = performance.now();

function formatDurationMs(durationMs) {
  return `${durationMs >= 100 ? durationMs.toFixed(0) : durationMs.toFixed(1)} ms`;
}

function logRendererBoot(step) {
  console.log(`[renderer-startup] ${step} at ${formatDurationMs(performance.now() - rendererBootStart)}`);
}

logRendererBoot("main.js module evaluation started");

import { createApp } from "vue";
import App from "./App.vue";
import "./styles.css";

logRendererBoot("imports resolved");

const app = createApp(App);
logRendererBoot("createApp completed");

app.mount("#app");
logRendererBoot("mount completed");
