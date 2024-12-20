import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { DEV_PORT, API_PORT, HOSTNAME, API_PREFIX, API_V1_STR } from './src/lib/generated_config.js';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		proxy: {
			[API_PREFIX]: {
				target: `http://${HOSTNAME}:${API_PORT}`,
				changeOrigin: true,
				rewrite: (path) => {
					if (!path.includes(API_V1_STR)) {
						return path.replace(API_PREFIX, API_V1_STR);
					}
					return path;
				},
				configure: (proxy, _options) => {
					proxy.on('error', (err, _req, _res) => {
						console.log('proxy error', err);
					});
					proxy.on('proxyReq', (proxyReq, req, _res) => {
						console.log('Sending Request to the Target:', req.method, req.url);
					});
					proxy.on('proxyRes', (proxyRes, req, _res) => {
						console.log('Received Response from the Target:', proxyRes.statusCode, req.url);
					});
				}
			},
			'/ws': {
				target: `ws://${HOSTNAME}:${API_PORT}`,
				ws: true,
				changeOrigin: true
			}
		},
		host: true,
		port: DEV_PORT,
		strictPort: true,
		hmr: {
				host: HOSTNAME,
				protocol: 'ws',
				clientPort: DEV_PORT
		},
		headers: {
			'Access-Control-Allow-Origin': '*',
			'Access-Control-Allow-Private-Network': 'true',
			'Access-Control-Allow-Methods': 'GET,HEAD,PUT,PATCH,POST,DELETE',
			'Access-Control-Allow-Headers': 'Content-Type'
		}
	},
	preview: {
		host: true,
		port: DEV_PORT,
		strictPort: true
	}
});