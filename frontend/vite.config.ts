import { defineConfig } from "vitest/config";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  esbuild: {
    jsx: "automatic",
  },
  plugins: [
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["pahadpath.svg"],
      workbox: {
        navigateFallback: "/index.html",
        globPatterns: ["**/*.{js,css,html,svg,webmanifest,woff2}"],
        runtimeCaching: [],
      },
      manifest: {
        name: "PahadPath",
        short_name: "PahadPath",
        description:
          "Find local homestays near quieter places in Uttarakhand.",
        theme_color: "#FBF4EA",
        background_color: "#FBF4EA",
        display: "standalone",
        start_url: "/",
        icons: [
          {
            src: "/pahadpath.svg",
            sizes: "any",
            type: "image/svg+xml",
            purpose: "any maskable",
          },
        ],
      },
    }),
  ],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
