import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  server: {
    port: 3000,
    host: "0.0.0.0",
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname),
      "@types": path.resolve(__dirname, "types.ts"),
      "@services": path.resolve(__dirname, "services"),
      "@domains": path.resolve(__dirname, "domains"),
      "@components": path.resolve(__dirname, "components"),
      "@utils": path.resolve(__dirname, "utils"),
    },
  },
});
