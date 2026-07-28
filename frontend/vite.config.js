import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Cloud dev environments (Codespaces, Gitpod, etc.) reach this server
    // through a forwarding proxy on a *.app.github.dev-style hostname, not
    // "localhost" — `host: true` binds all interfaces so the proxy can
    // reach the process, and `allowedHosts: true` disables Vite's
    // same-host request check (which otherwise rejects the proxy's Host
    // header as a DNS-rebinding protection). Both are no-ops for a normal
    // local `npm run dev`.
    host: true,
    allowedHosts: true,
  },
});
