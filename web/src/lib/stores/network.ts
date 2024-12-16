import { writable } from 'svelte/store';

export interface NetworkMode {
    mode: string;
    is_switching: boolean;
}

export const networkMode = writable<NetworkMode | null>(null); 