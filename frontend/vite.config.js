import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During development, React runs on Vite's server (localhost:5173) and Flask on localhost:5000.
// The proxy forwards every /api request to Flask, so the browser sees one origin:
// the session cookie keeps working and no CORS setup is needed.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:5000",
    },
  },
});
