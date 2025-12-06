import path from "path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  base: "/TripleThreatx2/",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      // send frontend requests to Flask on :5000 during dev
      "/auth": { target: "http://localhost:5000", changeOrigin: true },
      "/api":  { target: "http://localhost:5000", changeOrigin: true },
    },
  },
});
