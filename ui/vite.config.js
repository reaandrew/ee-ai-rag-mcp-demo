import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(path.dirname(''), './src'),
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@import "./src/styles/variables.scss";`,
      },
    },
  },
  server: {
    proxy: {
      // Configure proxy to handle CORS during development
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true,
        rewrite: (pathStr) => pathStr.replace(/^\/api/, ''),
        configure: (proxy) => {
          proxy.on('error', (err) => {
            console.log('proxy error', err);
          });
          proxy.on('proxyReq', (proxyReq, req) => {
            console.log('Sending Request:', req.method, req.url);
          });
          proxy.on('proxyRes', (proxyRes, req) => {
            console.log('Received Response:', proxyRes.statusCode, req.url);
          });
        },
      },
      // Special proxy for AWS API Gateway
      '/aws-api': {
        target: '',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq, req) => {
            // Get the target URL from the request query parameters
            const targetUrl = req.url.split('?target=')[1];
            if (targetUrl) {
              // Set the target URL for this request
              proxy.options.target = decodeURIComponent(targetUrl);
              console.log(`Proxying to: ${proxy.options.target}`);
            }
          });
        },
        rewrite: (pathStr) => {
          // Remove the /aws-api prefix and any query parameters
          return pathStr.replace(/^\/aws-api/, '').split('?')[0];
        },
      },
    },
  },
});