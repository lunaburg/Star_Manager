import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";
import localizationPlugin from "./scripts/localize-vue.mjs";

export default defineConfig({
  base: "./",
  plugins: [localizationPlugin(), vue()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true
  },
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});
