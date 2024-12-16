import { browser } from '$app/environment';

// Get the hostname dynamically, only in browser
const hostname = browser ? window.location.hostname : '';

// API Configuration
export const API_V1_STR = '/api/v1';
export const WS_PATH = '/ws';
export const API_PORT = 80;
export const DEV_PORT = 5173;

// Base URLs for API and WebSocket connections
export const API_BASE_URL = browser ? (
    import.meta.env.VITE_API_BASE_URL || 
    (window.location.port === DEV_PORT.toString() 
        ? `http://${hostname}:${API_PORT}` 
        : '')
) : '';

export const WS_URL = browser ? (
    import.meta.env.VITE_WS_URL || 
    `ws://${hostname}${API_V1_STR}${WS_PATH}`
) : '';