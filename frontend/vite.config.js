import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During development the Python API runs on :8000 and Vite serves the React app
// on :5173. We proxy /api to the backend so the browser sees a single origin.
// `npm run build` emits static assets into ../app/web so the Python server can
// serve the built React app directly in production (one `python -m app.server`).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.STUDYBUDDY_API || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    // Build into app/web_dist so the Python server auto-serves the compiled
    // React SPA while the zero-build vanilla app/web stays intact as a fallback.
    outDir: "../app/web_dist",
    emptyOutDir: true,
  },
});
