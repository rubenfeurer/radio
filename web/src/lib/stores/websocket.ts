import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import { WS_URL } from '$lib/config';
import { currentMode } from './mode';  // Import the mode store

interface WSMessage {
    type: 'status_update' | 'mode_update' | 'wifi_update' | 'monitor_update';
    data?: any;
}

export const createWebSocketStore = () => {
    const { subscribe, set } = writable<WebSocket | null>(null);
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout>;
    let isIntentionalClose = false;

    const connect = () => {
        if (!browser) return;

        if (ws) {
            isIntentionalClose = true;
            ws.close();
        }

        console.log('Connecting to WebSocket URL:', WS_URL);
        ws = new WebSocket(WS_URL);
        
        ws.onopen = () => {
            console.log('WebSocket connected to:', WS_URL);
            set(ws);
            isIntentionalClose = false;
        };

        ws.onmessage = (event) => {
            try {
                const message: WSMessage = JSON.parse(event.data);
                console.log('WebSocket message received:', message);

                if (message.type === 'monitor_update' && message.data?.systemInfo?.mode) {
                    const rawMode = message.data.systemInfo.mode;
                    const mode = rawMode.toLowerCase();
                    console.log('Mode update:', { rawMode, normalizedMode: mode });
                    
                    if (mode === 'ap' || mode === 'client') {
                        currentMode.set(mode);
                        console.log('Current mode set to:', mode);
                    } else {
                        console.error('Invalid mode received:', rawMode);
                    }
                }

                // Update websocketStore
                websocketStore.set({ data: message });
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };

        ws.onclose = (event) => {
            console.log(`WebSocket closed: ${event.code}`);
            set(null);
            
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

    if (browser) {
        connect();
    }

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

// Create and export the store
export const ws = createWebSocketStore();
// Create a derived store for WebSocket data
export const websocketStore = writable<{
    data?: {
        type: string;
        mode?: 'ap' | 'client';
        [key: string]: any;
    };
}>({});

// Update websocketStore when messages are received
if (browser) {
    ws.subscribe(($ws) => {
        if ($ws) {
            $ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    websocketStore.set({ data: message });
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };
        }
    });
}

