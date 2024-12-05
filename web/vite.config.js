import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		proxy: {
			'/api': {
				target: 'http://radiod.local:8000',
				changeOrigin: true,
				rewrite: (path) => {
					// Add /v1 to the path if it's not already there
					if (!path.includes('/v1/')) {
						return path.replace('/api/', '/api/v1/');
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
				target: 'ws://radiod.local:8000',
				ws: true
			}
		},
		host: true
	}
});