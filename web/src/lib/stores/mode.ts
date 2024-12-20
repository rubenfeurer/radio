import { writable } from 'svelte/store';

// Define valid mode types
export type NetworkMode = 'ap' | 'client';

// Initialize with undefined to show error state until we get real data
export const currentMode = writable<NetworkMode | undefined>(undefined); 