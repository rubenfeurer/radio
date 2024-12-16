// Get the hostname dynamically
const hostname = window.location.hostname;

// Base URLs for API and WebSocket connections
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || `http://${hostname}:8000`;
export const WS_URL = import.meta.env.VITE_WS_URL || `ws://${hostname}:8000`; 