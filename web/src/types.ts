import type { NetworkStatus } from '$lib/types';

export interface RadioStation {
    id: number;
    name: string;
    url: string;
    country?: string;
    location?: string;
    slot?: number;
}

// WiFi related types
export interface WiFiNetwork {
    ssid: string;
    security: string | null;
    signal_strength: number;
    in_use: boolean;
    saved: boolean;
}

export interface CurrentConnection {
    ssid: string | null;
    is_connected: boolean;
}

export interface WiFiStatus {
    ssid: string | null;
    signal_strength: number;
    is_connected: boolean;
    has_internet: boolean;
    available_networks: WiFiNetwork[];
    preconfigured_ssid?: string;
}

export interface NetworkStatus {
    wifi_status: WiFiStatus;
    mode_status: {
        mode: 'client' | 'ap';
        is_switching: boolean;
    };
} 