<script lang="ts">
  import { Card, Badge, Button } from 'flowbite-svelte';
  import { browser } from '$app/environment';
  import { onMount } from 'svelte';

  interface WiFiNetwork {
    ssid: string;
    signal_strength: number;
    security: string | null;
    in_use: boolean;
  }

  interface WiFiStatusData {
    ssid: string | null;
    signal_strength: number | null;
    is_connected: boolean;
    has_internet: boolean;
    available_networks: WiFiNetwork[];
  }

  let wifiStatus: WiFiStatusData = {
    ssid: null,
    signal_strength: null,
    is_connected: false,
    has_internet: false,
    available_networks: []
  };

  const currentHost = browser ? window.location.hostname : '';
  const API_BASE = browser 
    ? (window.location.port === '5173' 
      ? `http://${currentHost}:80`
      : '')
    : '';

  onMount(async () => {
    await fetchWiFiStatus();
  });

  async function fetchWiFiStatus() {
    try {
      const response = await fetch(`${API_BASE}/api/v1/wifi/status`);
      if (!response.ok) {
        console.error('Failed to fetch WiFi status:', await response.text());
        return;
      }
      const data = await response.json();
      wifiStatus = data;
    } catch (error) {
      console.error("Failed to fetch WiFi status:", error);
    }
  }

  // Simple SVG icons
  const WifiIcon = {
    on: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
    </svg>`,
    off: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>`
  };

  const LockIcon = `<svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
  </svg>`;
</script>

<Card class="mb-4">
  <div class="flex flex-col gap-2">
    <span class="text-sm text-gray-500">WiFi</span>
    <div class="flex items-center gap-2">
      <h3 class="text-lg font-semibold">
        {wifiStatus.ssid || 'Not connected'}
      </h3>
      {#if wifiStatus.is_connected}
        {#if wifiStatus.has_internet}
          {@html WifiIcon.on}
        {/if}
        {#if wifiStatus.available_networks.find(n => n.ssid === wifiStatus.ssid)?.security}
          {@html LockIcon}
        {/if}
      {:else}
        <Badge color="red">
          {@html WifiIcon.off}
          Disconnected
        </Badge>
      {/if}
    </div>
    <a href="/wifi" class="w-full">
      <Button color="alternative" class="w-full mt-2">
        Settings
      </Button>
    </a>
  </div>
</Card> 