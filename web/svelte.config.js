import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),

	kit: {
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: 'index.html',
			precompress: false,
			strict: true
		}),
		paths: {
			base: '',
			assets: ''
		},
		appDir: 'app',
		files: {
			assets: 'static',
			lib: 'src/lib',
			routes: 'src/routes'
		},
		prerender: {
			handleMissingId: 'ignore'
		}
	}
};

export default config;
