import { defineConfig, devices } from "@playwright/test";

const frontendPort = 14173;
const frontendBaseUrl = `http://127.0.0.1:${frontendPort}`;

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /.*\.e2e\.ts/,
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  expect: {
    timeout: 15_000
  },
  globalSetup: "./tests/e2e/support/global-setup.ts",
  outputDir: "./test-results/e2e",
  reporter: [["list"], ["html", {
    open: "never",
    outputFolder: "./test-results/e2e-report"
  }]],
  use: {
    ...devices["Desktop Chrome"],
    baseURL: frontendBaseUrl,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "retain-on-failure"
  },
  webServer: {
    command: "node tests/e2e/support/e2e-environment.mjs",
    url: frontendBaseUrl,
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: "pipe",
    stderr: "pipe"
  }
});
