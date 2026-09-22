import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxies /api straight to the FastAPI backend during local dev, so the
// frontend never has to think about CORS or hardcode a backend URL.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
