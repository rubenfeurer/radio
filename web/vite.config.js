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
				rewrite: (path) => path.includes(API_V1_STR) ? path : path.replace(API_PREFIX, API_V1_STR)
			},
			'/ws': {
				target: `ws://${HOSTNAME}:${API_PORT}`,
				ws: true,
				changeOrigin: true
			}
		},
		host: '0.0.0.0',
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
			'Access-Control-Allow-Headers': 'Content-Type, Origin, Accept, Authorization, Content-Length, X-Requested-With',
			'Access-Control-Allow-Credentials': 'true',
			'Cross-Origin-Opener-Policy': 'same-origin',
			'Cross-Origin-Embedder-Policy': 'require-corp',
			'Cross-Origin-Resource-Policy': 'cross-origin',
			'Permissions-Policy': 'interest-cohort=()'
		},
		cors: {
			origin: '*',
			methods: ['GET', 'HEAD', 'PUT', 'PATCH', 'POST', 'DELETE'],
			allowedHeaders: ['Content-Type', 'Authorization'],
			exposedHeaders: ['Content-Range', 'X-Content-Range'],
			credentials: true,
			maxAge: 3600
		}
	},
	preview: {
		host: '0.0.0.0',
		port: DEV_PORT,
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