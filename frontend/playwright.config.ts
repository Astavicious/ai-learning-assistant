import {defineConfig,devices} from '@playwright/test';
export default defineConfig({
  testDir:'./e2e', fullyParallel:false, workers:1,
  use:{baseURL:process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:5173',trace:'retain-on-failure'},
  projects:[{name:'desktop',use:{...devices['Desktop Chrome'],viewport:{width:1440,height:1000}}},{name:'mobile',use:{...devices['iPhone 13'],defaultBrowserType:'chromium'}}],
  webServer:process.env.PLAYWRIGHT_BASE_URL ? undefined : {command:'npm run dev',url:'http://127.0.0.1:5173',reuseExistingServer:true},
});
