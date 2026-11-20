import { defineConfig } from "@playwright/test";

const PORT = 8103;

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  use: {
    baseURL: `http://localhost:${PORT}`,
    viewport: { width: 1360, height: 900 },
    launchOptions: process.env.PW_CHROME ? { executablePath: process.env.PW_CHROME } : {},
  },
  // the service serves the built dashboard, the committed reports and the demo world
  webServer: {
    command: `cd .. && CAP_DATABASE_URL=sqlite+pysqlite:///:memory: python -m uvicorn cap.service.api:app --port ${PORT}`,
    url: `http://localhost:${PORT}/health`,
    reuseExistingServer: !process.env.CI,
    timeout: 90_000,
  },
  reporter: [["list"]],
});
