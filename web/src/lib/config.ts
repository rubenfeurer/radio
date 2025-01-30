import { browser } from '$app/environment';
import config from './generated_config.json';

// Get the hostname dynamically, only in browser
const hostname = browser ? window.location.hostname : '';

// Import configuration from Python-generated file
export const API_V1_STR = config.API_V1_STR;
export const WS_PATH = config.WS_PATH;
export const API_PORT = config.API_PORT;
export const DEV_PORT = config.DEV_PORT;
export const PROD_PORT = config.PROD_PORT;

// Base URLs for API and WebSocket connections
export const API_BASE_URL = browser ? (
    import.meta.env.VITE_API_BASE_URL ||
    (window.location.port === DEV_PORT.toString()
        ? `http://${hostname}:${API_PORT}`
        : '')
) : '';

export const WS_URL = browser ? (
    import.meta.env.VITE_WS_URL ||
    (window.location.port === DEV_PORT.toString()
        ? `ws://${hostname}:${API_PORT}${API_V1_STR}${WS_PATH}`
        : `ws://${hostname}${API_V1_STR}${WS_PATH}`)
) : '';
