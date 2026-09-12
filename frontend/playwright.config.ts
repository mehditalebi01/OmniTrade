import { defineConfig } from '@playwright/test';
export default defineConfig({testDir:'./e2e',use:{baseURL:'http://127.0.0.1:5173'},webServer:[{command:'../.venv/Scripts/python -m uvicorn omnitrade.api:app --port 8000',url:'http://127.0.0.1:8000/health',cwd:'..',reuseExistingServer:true},{command:'pnpm dev',url:'http://127.0.0.1:5173',reuseExistingServer:true}]});
