import { writable } from 'svelte/store';
import { browser } from '$app/environment';

interface WebSocketStore {
  connected: boolean;
  monitorConnected: boolean;
  error: string | null;
  ws: WebSocket | null;
  networkMode?: string;
  is_switching?: boolean;
}

interface WebSocketMessage {
  type: string;
  data?: any;
}

function createWebSocketStore() {
  const { subscribe, set, update } = writable<WebSocketStore>({
    connected: false,
    monitorConnected: false,
    error: null,
    ws: null,
    networkMode: 'unknown',
    is_switching: false
  });

  let reconnectTimer: ReturnType<typeof setTimeout>;

  function connect(url: string) {
    if (!browser) return;

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        update(store => ({ ...store, connected: true, error: null, ws }));
        ws.send(JSON.stringify({ type: "status_request" }));
      };

      ws.onclose = () => {
        update(store => ({ ...store, connected: false, ws: null }));
        setTimeout(() => connect(url), 1000);
      };

      ws.onerror = (error) => {
        update(store => ({ ...store, error: 'WebSocket error occurred' }));
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          handleMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

    } catch (error) {
      console.error('Error creating WebSocket:', error);
      setTimeout(() => connect(url), 1000);
    }
  }

  function handleMessage(message: WebSocketMessage) {
    switch (message.type) {
      case 'monitor_update':
        update(store => ({ 
          ...store, 
          monitorConnected: true,
          networkMode: message.data?.systemInfo?.networkMode || 'unknown',
          is_switching: message.data?.systemInfo?.is_switching || false
        }));
        break;
      case 'status_update':
        update(store => ({ ...store, monitorConnected: false }));
        break;
    }
  }

  return {
    subscribe,
    setConnected: (status: boolean) => update(store => ({ ...store, connected: status })),
    setMonitorConnected: (status: boolean) => update(store => ({ ...store, monitorConnected: status })),
    setError: (error: string | null) => update(store => ({ ...store, error }))
  };
}

export const wsStore = createWebSocketStore();
