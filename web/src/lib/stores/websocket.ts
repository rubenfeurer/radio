import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import { WS_URL } from '$lib/config';
import { currentMode, type NetworkMode } from './mode';
import { API_V1_STR } from '$lib/config';

interface WSMessage {
    type: 'status_update' | 'mode_update' | 'wifi_update' | 'monitor_update';
    data?: any;
}

export const createWebSocketStore = () => {
    if (!browser) {
        return {
            subscribe: () => () => { },
            sendMessage: () => { },
            disconnect: () => { }
        };
    }

    console.log('Initializing WebSocket store with URL:', WS_URL);
    const { subscribe, set } = writable<WebSocket | null>(null);
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout>;
    let isIntentionalClose = false;

    const connect = () => {
        if (ws) {
            console.log('Closing existing WebSocket connection');
            isIntentionalClose = true;
            ws.close();
        }

        console.log('Attempting WebSocket connection to:', WS_URL);
        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            console.log('WebSocket connected successfully');
            set(ws);
            isIntentionalClose = false;
            sendMessage({ type: 'status_request' });
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                console.log('WebSocket message received:', message);
                websocketStore.set({ data: message });

                if (message.type === 'status_response') {
                    console.log('Processing status response:', message.data);
                }
            } catch (error) {
                console.error('Error processing WebSocket message:', error);
            }
        };

        ws.onclose = (event) => {
            console.log('WebSocket closed:', event.code, event.reason);
            set(null);

            if (!isIntentionalClose && browser) {
                console.log('Scheduling reconnection attempt...');
                reconnectTimer = setTimeout(connect, 1000);
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    };

    // Initial connection
    connect();

    return {
        subscribe,
        sendMessage: (message: any) => {
            if (ws?.readyState === WebSocket.OPEN) {
                console.log('Sending WebSocket message:', message);
                ws.send(JSON.stringify(message));
            } else {
                console.warn('WebSocket not ready, message not sent:', message);
            }
        },
        disconnect: () => {
            console.log('Disconnecting WebSocket...');
            isIntentionalClose = true;
            clearTimeout(reconnectTimer);
            if (ws) ws.close();
        }
    };
};

// Create and export the store
export const ws = createWebSocketStore();
// Create a derived store for WebSocket data
export const websocketStore = writable<{ data?: WSMessage }>({});

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

function handleWebSocketMessage(event: MessageEvent) {
    try {
        const data = JSON.parse(event.data);
        console.log('WebSocket message received:', data);

        if (data.type === 'status_response') {
            console.log('Processing status response:', data.data);

            // Set mode from status response
            if (data.data.mode) {
                const mode = data.data.mode.toLowerCase() as NetworkMode;
                console.log('Setting mode to:', mode);
                if (mode === 'ap' || mode === 'client') {
                    currentMode.set(mode);
                }
            }
        }

        // Handle mode_update messages as well
        if (data.type === 'mode_update') {
            const mode = data.mode.toLowerCase() as NetworkMode;
            console.log('Mode update received:', mode);
            if (mode === 'ap' || mode === 'client') {
                currentMode.set(mode);
            }
        }
    } catch (error) {
        console.error('Error handling WebSocket message:', error);
    }
}
