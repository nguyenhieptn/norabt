import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Build output goes straight to Agent/web/dist -- app.py serves
// Agent/web/dist/index.html at "/" and Agent/web/dist/assets/* at
// "/assets/" (see Agent/backend/web/app.py's static-file handling and
// Agent/deploy/nginx-agent*.conf.template's own "location /assets/").
// docker-compose.yml already bind-mounts the WHOLE Agent/web/ directory
// read-only into the container (`../web:/app/Agent/web:ro`) -- this just
// needs to land inside it, no compose change required (see
// Agent/deploy/README.md's "Frontend build" section, which verifies this
// claim rather than assuming it).
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: path.resolve(__dirname, "../web/dist"),
    // Stale files from a previous build (a since-renamed chunk, ...) must
    // never linger in Agent/web/dist -- a half-old, half-new bundle is
    // worse than a clean rebuild.
    emptyOutDir: true,
    // No sourcemaps in the production build -- this host runs 15 other
    // production sites under a hard resource ceiling (see build.sh's own
    // header comment and Agent/deploy/README.md); sourcemaps are extra
    // build time/output size for a debugging aid nobody on the open
    // internet needs shipped to them.
    sourcemap: false,
  },
});
