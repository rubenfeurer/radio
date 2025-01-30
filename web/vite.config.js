import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { DEV_PORT, API_PORT, HOSTNAME, API_PREFIX, API_V1_STR } from './src/lib/generated_config.js';

// Get IP address from hostname if it's an IP
const isIP = (host) => /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/.test(host);
const hostIP = isIP(HOSTNAME) ? HOSTNAME : '127.0.0.1';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		host: '0.0.0.0',
		port: DEV_PORT,
		strictPort: true,
		fs: {
			allow: ['..']
		},
		watch: {
			usePolling: true
		},
		https: false,
		proxy: {
			[API_PREFIX]: {
				target: `http://localhost:${API_PORT}`,
				changeOrigin: true,
				rewrite: (path) => path.includes(API_V1_STR) ? path : path.replace(API_PREFIX, API_V1_STR)
			},
			'/ws': {
				target: `ws://localhost:${API_PORT}`,
				ws: true,
				changeOrigin: true,
				rewrite: (path) => path.includes(API_V1_STR) ? path : `${API_V1_STR}${path}`
			}
		},
		headers: {
			'Access-Control-Allow-Origin': '*',
			'Access-Control-Allow-Methods': 'GET,HEAD,PUT,PATCH,POST,DELETE',
			'Access-Control-Allow-Headers': 'Content-Type, Authorization'
		},
		// Use dynamic hostname and IP
		allowedHosts: [
			'localhost',
			hostIP,
			HOSTNAME,
			'*.local'
		]
	},
	preview: {
		host: '0.0.0.0',
		port: DEV_PORT,
		strictPort: true,
		proxy: {
			[API_PREFIX]: {
				target: `http://${HOSTNAME}:${API_PORT}`,
				changeOrigin: true,
				rewrite: (path) => path.includes(API_V1_STR) ? path : path.replace(API_PREFIX, API_V1_STR)
			},
			'/ws': {
				target: `ws://${HOSTNAME}:${API_PORT}`,
				ws: true,
				changeOrigin: true
			}
		}
	}
});
