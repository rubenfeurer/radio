import { writable } from 'svelte/store';

export const currentMode = writable<'ap' | 'client'>('client'); 