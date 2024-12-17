import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import { WS_URL } from '$lib/config';

interface WSMessage {
    type: string;
    data?: any;
}

export const createWebSocketStore = () => {
    const { subscribe, set } = writable<WebSocket | null>(null);
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout>;
    let isIntentionalClose = false;

    const connect = () => {
        // Only connect in browser environment
        if (!browser) return;

        // Clear any existing connection
        if (ws) {
            isIntentionalClose = true;
            ws.close();
        }

        ws = new WebSocket(WS_URL);
        
        ws.onopen = () => {
            console.log('WebSocket connected');
            set(ws);
            isIntentionalClose = false;
        };

        ws.onclose = (event) => {
            console.log(`WebSocket closed: ${event.code}`);
            set(null);
            
            // Only reconnect if not intentionally closed and in browser
            if (!isIntentionalClose && browser) {
                reconnectTimer = setTimeout(connect, 1000);
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            if (ws) ws.close();
        };
    };

    const sendMessage = (message: WSMessage) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message));
        }
    };

    // Start initial connection only in browser
    if (browser) {
        connect();
    }

    // Cleanup on unmount
    return {
        subscribe,
        sendMessage,
        disconnect: () => {
            if (!browser) return;
            isIntentionalClose = true;
            clearTimeout(reconnectTimer);
            if (ws) ws.close();
        }
    };
};

// Create the store
export const ws = createWebSocketStore();
