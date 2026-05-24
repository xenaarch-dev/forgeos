import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    coverage: { reporter: ["text"], thresholds: { lines: 80, functions: 80, branches: 70 } },
  },
});
