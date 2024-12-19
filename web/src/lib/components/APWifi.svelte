<script lang="ts">
  import { Card, Button, Badge, Input, Alert } from 'flowbite-svelte';
  import { browser } from '$app/environment';
  import { onMount } from 'svelte';
  import { ws } from '$lib/stores/websocket';
  import { currentMode } from '$lib/stores/mode';

  interface WiFiNetwork {
    ssid: string;
    security: string | null;
    signal_strength: number;
    in_use: boolean;
    saved: boolean;
  }

  interface APStatus {
    is_ap_mode: boolean;
    ap_ssid: string | null;
    available_networks: WiFiNetwork[];
    saved_networks: string[];
    preconfigured_ssid: string | null;
  }

  let networks: WiFiNetwork[] = [];
  let selectedNetwork: WiFiNetwork | null = null;
  let password = '';
  let scanning = false;
  let connecting = false;
  let error: string | null = null;
  let apStatus: APStatus | null = null;
  let scanWarningVisible = false;

  const currentHost = browser ? window.location.hostname : '';
  const API_BASE = browser 
    ? (window.location.port === '5173' 
      ? `http://${currentHost}:80`
      : '')
    : '';

  // SVG icons (reused from ClientWifi)
  const Icons = {
    arrowLeft: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
    </svg>`,
    lock: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
    </svg>`,
    wifiStrong: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
    </svg>`
  };

  function getWifiIcon(signal_strength: number): string {
    return Icons.wifiStrong; // Simplified for AP mode
  }

  onMount(async () => {
    await fetchAPStatus();
    // Subscribe to WebSocket updates
    ws.subscribe(socket => {
      if (socket) {
        socket.addEventListener('message', handleWebSocketMessage);
      }
    });
  });

  function handleWebSocketMessage(event: MessageEvent) {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'mode_update') {
        if (data.mode === 'client') {
          // Successfully connected and switched to client mode
          window.location.reload();
        } else if (data.mode === 'ap') {
          // Handle AP mode switch
          if (data.available_networks) {
            // Use pre-scanned networks
            networks = data.available_networks;
            scanning = false;
          }
          if (data.ap_ssid) {
            apStatus = {
              ...apStatus,
              ap_ssid: data.ap_ssid,
              is_ap_mode: true,
              available_networks: data.available_networks || []
            };
          }
        }
      } else if (data.type === 'ap_scan_complete') {
        scanning = false;
        networks = data.networks;
      }
    } catch (e) {
      console.error('Error handling WebSocket message:', e);
    }
  }

  async function fetchAPStatus() {
    try {
      const response = await fetch(`${API_BASE}/api/v1/ap/status`);
      if (!response.ok) throw new Error('Failed to fetch AP status');
      apStatus = await response.json();
      networks = apStatus.available_networks;
    } catch (e) {
      console.error('Error fetching AP status:', e);
      error = 'Failed to fetch AP status';
    }
  }

  async function scanNetworks() {
    if (!scanWarningVisible) {
      scanWarningVisible = true;
      return;
    }
    
    scanning = true;
    error = null;
    scanWarningVisible = false;
    
    try {
      networks = [{ ssid: 'Scanning...', security: null, signal_strength: 0, in_use: false, saved: false }];
      
      const response = await fetch(`${API_BASE}/api/v1/ap/scan`, {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error('Failed to scan networks');
      }
      
      const newNetworks = await response.json();
      networks = newNetworks;
      
    } catch (e) {
      console.error('Error scanning networks:', e);
      error = 'Failed to scan networks. Please try again.';
    } finally {
      scanning = false;
    }
  }

  async function connectToNetwork(network: WiFiNetwork) {
    if (!network.security) {
      await attemptConnection(network.ssid, '');
    } else {
      selectedNetwork = network;
    }
  }

  async function attemptConnection(ssid: string, password: string) {
    connecting = true;
    error = null;
    try {
      const response = await fetch(`${API_BASE}/api/v1/ap/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ssid, password })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Connection failed');
      }

      // Connection successful - wait for mode change via WebSocket
    } catch (e) {
      console.error('Connection error:', e);
      error = e.message;
    } finally {
      connecting = false;
    }
  }
</script>

<div class="container mx-auto p-4 max-w-2xl">
  <div class="mb-4">
    {#if apStatus?.ap_ssid}
      <Alert color="info">
        Connected to Access Point: {apStatus.ap_ssid}
      </Alert>
    {/if}
  </div>

  {#if error}
    <Alert color="red" class="mb-4">
      {error}
    </Alert>
  {/if}

  <Card class="mb-4">
    <div class="flex justify-between items-center">
      <h2 class="text-xl font-bold">Available Networks</h2>
      <Button
        size="sm"
        color="blue"
        disabled={scanning}
        on:click={scanNetworks}
      >
        {scanning ? 'Scanning...' : 'Scan'}
      </Button>
    </div>
  </Card>

  {#if scanWarningVisible}
    <Alert color="warning" class="mb-4">
      <span class="font-medium">Warning!</span>
      Scanning for networks will temporarily disconnect your device. You will need to reconnect to the AP afterward.
      <div class="mt-2 flex gap-2">
        <Button color="red" size="sm" on:click={() => scanWarningVisible = false}>Cancel</Button>
        <Button color="green" size="sm" on:click={scanNetworks}>Continue</Button>
      </div>
    </Alert>
  {/if}

  {#if selectedNetwork}
    <Card class="mb-4">
      <h3 class="text-lg mb-4">Connect to {selectedNetwork.ssid}</h3>
      <form on:submit|preventDefault={() => attemptConnection(selectedNetwork.ssid, password)}>
        <Input
          type="password"
          placeholder="Network password"
          bind:value={password}
          class="mb-4"
        />
        <div class="flex gap-2">
          <Button type="submit" disabled={connecting}>
            {connecting ? 'Connecting...' : 'Connect'}
          </Button>
          <Button color="alternative" on:click={() => selectedNetwork = null}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  {:else}
    <div class="grid gap-4">
      {#each networks as network}
        <Card 
          class="w-full cursor-pointer hover:bg-gray-50 transition-colors"
          on:click={() => connectToNetwork(network)}
        >
          <div class="flex items-center justify-between p-1">
            <div class="flex items-center gap-3">
              {@html getWifiIcon(network.signal_strength)}
              <span class="font-semibold">{network.ssid}</span>
              {#if network.security}
                {@html Icons.lock}
              {/if}
              {#if network.ssid === apStatus?.preconfigured_ssid}
                <Badge color="blue">Preconfigured</Badge>
              {/if}
            </div>
            <Badge color="dark">
              {network.signal_strength}%
            </Badge>
          </div>
        </Card>
      {/each}
    </div>
  {/if}
</div> 