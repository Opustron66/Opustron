import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // P4's egress log server (python -m chronicle.guard.egress_server). Listed
      // first so it wins over the general /api rule. 127.0.0.1, not localhost:
      // Node may resolve localhost to ::1 and the server only listens on IPv4.
      "/api/egress": {
        target: "http://127.0.0.1:8001",
      },
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.js"],
    // West of UTC, so date-only values that render in local time show the wrong day.
    env: { TZ: "America/Los_Angeles" },
  },
});
