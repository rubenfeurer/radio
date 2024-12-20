<script lang="ts">
  import { Card, Button, Badge, Input, Skeleton } from 'flowbite-svelte';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { ws } from '$lib/stores/websocket';
  import { onMount } from 'svelte';
  import { API_V1_STR } from '$lib/config';  // Import API_V1_STR

  // Get the current hostname (IP or domain)
  const currentHost = browser ? window.location.hostname : '';

  // SVG icons
  const Icons = {
    arrowLeft: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
    </svg>`,
    lock: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
    </svg>`,
    wifiStrong: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
    </svg>`,
    wifiGood: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0" />
    </svg>`,
    wifiFair: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01" />
    </svg>`,
    wifiWeak: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 20h.01" />
    </svg>`
  };

  // Add a helper function to get the appropriate WiFi icon
  function getWifiIcon(signal_strength: number): string {
    if (signal_strength >= 80) return Icons.wifiStrong;
    if (signal_strength >= 60) return Icons.wifiGood;
    if (signal_strength >= 40) return Icons.wifiFair;
    return Icons.wifiWeak;
  }

  interface WiFiNetwork {
    ssid: string;
    security: string | null;
    signal_strength: number;
    in_use: boolean;
    saved: boolean;
  }

  interface CurrentConnection {
    ssid: string | null;
    is_connected: boolean;
  }

  let networks: WiFiNetwork[] = [];
  let savedNetworks: WiFiNetwork[] = [];
  let otherNetworks: WiFiNetwork[] = [];
  let currentConnection: CurrentConnection | null = null;
  let selectedNetwork: WiFiNetwork | null = null;
  let password = '';
  let connecting = false;
  let loading = true;
  let preconfiguredSSID: string | null = null;
  let wsConnected = false;
  ws.subscribe(socket => {
    wsConnected = socket !== null;
  });

  onMount(async () => {
    await Promise.all([
      fetchNetworks(),
      fetchCurrentConnection()
    ]);
    // Request initial WiFi status
    ws.sendMessage({ type: "wifi_status_request" });
  });

  async function fetchCurrentConnection() {
    try {
      const response = await fetch(`${API_V1_STR}/wifi/current`);
      if (!response.ok) throw new Error('Failed to fetch current connection');
      currentConnection = await response.json();
    } catch (error) {
      console.error('Error fetching current connection:', error);
    }
  }

  async function fetchNetworks() {
    loading = true;
    try {
      const statusResponse = await fetch(`${API_V1_STR}/wifi/status`);
      if (!statusResponse.ok) throw new Error('Failed to fetch status');
      const status = await statusResponse.json();
      
      // Get networks from status response
      const rawNetworks = status.available_networks;
      preconfiguredSSID = status.preconfigured_ssid;

      // Filter out networks with empty SSIDs
      networks = rawNetworks.filter(network => 
        network.ssid && network.ssid.trim() !== ''
      );
      
      // Mark current network as in_use and saved
      if (currentConnection?.ssid) {
        networks = networks.map(network => ({
          ...network,
          in_use: network.ssid === currentConnection.ssid,
          saved: network.ssid === currentConnection.ssid || network.saved
        }));
      }
      
      // Sort networks by signal strength (highest first)
      networks.sort((a, b) => b.signal_strength - a.signal_strength);
      
      // Split networks into saved and other
      savedNetworks = networks.filter(n => n.saved || n.in_use);
      otherNetworks = networks.filter(n => !n.saved && !n.in_use);
    } catch (error) {
      console.error('Error fetching networks:', error);
    } finally {
      loading = false;
    }
  }

  async function connectToNetwork(network: WiFiNetwork) {
    if (network.ssid === preconfiguredSSID) {
        // Use the dedicated preconfigured endpoint
        await connectToPreconfigured();
    } else if (!network.security || network.saved) {
        // Connect without password if network is open OR saved
        await attemptConnection(network.ssid, '');
    } else {
        selectedNetwork = network;
    }
  }

  async function attemptConnection(ssid: string, password: string) {
    connecting = true;
    try {
      const statusResponse = await fetch(`${API_V1_STR}/wifi/status`);
      if (statusResponse.ok) {
        const status = await statusResponse.json();
        // If the SSID matches the preconfigured one, use 'preconfigured' instead
        if (status.preconfigured_ssid && ssid === status.preconfigured_ssid) {
          ssid = 'preconfigured';
        }
      }

      const response = await fetch(`${API_V1_STR}/wifi/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ssid, password })
      });

      if (!response.ok) throw new Error('Failed to connect');
      
      await new Promise(resolve => setTimeout(resolve, 5000));
      
      const hostnameResponse = await fetch(`${API_V1_STR}/system/hostname`);
      if (hostnameResponse.ok) {
        const { hostname } = await hostnameResponse.json();
        window.location.href = `http://${hostname}`;
      } else {
        goto('/');
      }
    } catch (error) {
      console.error('Connection error:', error);
      alert('Failed to connect to network');
    } finally {
      connecting = false;
    }
  }

  async function connectToPreconfigured() {
    connecting = true;
    try {
      const response = await fetch(`${API_V1_STR}/wifi/connect/preconfigured`, {
        method: 'POST'
      });

      if (!response.ok) throw new Error('Failed to connect');
      
      await new Promise(resolve => setTimeout(resolve, 5000));
      
      const hostnameResponse = await fetch(`${API_V1_STR}/system/hostname`);
      if (hostnameResponse.ok) {
        const { hostname } = await hostnameResponse.json();
        window.location.href = `http://${hostname}`;
      } else {
        goto('/');
      }
    } catch (error) {
      console.error('Connection error:', error);
      alert('Failed to connect to preconfigured network');
    } finally {
      connecting = false;
    }
  }
</script>

<div class="container mx-auto p-4 max-w-2xl">
  <h1 class="text-2xl font-bold mb-4">Networks (Client Mode)</h1>

  {#if selectedNetwork}
    <Card class="w-full">
      <h2 class="text-xl mb-4">Connect to {selectedNetwork.ssid}</h2>
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
    <div class="grid gap-6 w-full">
      {#if loading}
        <div class="grid gap-4">
          {#each Array(3) as _}
            <Card class="w-full">
              <div class="flex items-center justify-between p-1">
                <div class="flex items-center gap-3">
                  <div class="w-4 h-4 bg-gray-200 rounded animate-pulse" />
                  <div class="h-5 bg-gray-200 rounded w-40 animate-pulse" />
                  <div class="w-4 h-4 bg-gray-200 rounded animate-pulse" />
                </div>
              </div>
            </Card>
          {/each}
        </div>
      {:else}
        <!-- Saved Networks Section -->
        {#if savedNetworks.length > 0}
          <div>
            <h2 class="text-lg font-semibold mb-3">Saved Networks</h2>
            <div class="grid gap-4">
              {#each savedNetworks as network}
                <Card class="w-full hover:bg-gray-50 transition-colors">
                  <div class="flex items-center justify-between p-1">
                    <div class="flex items-center gap-3">
                      {@html getWifiIcon(network.signal_strength)}
                      <span class="font-semibold">{network.ssid}</span>
                      {#if network.security}
                        {@html Icons.lock}
                      {/if}
                      {#if network.in_use}
                        <Badge color="green">Connected</Badge>
                      {/if}
                      {#if network.ssid === preconfiguredSSID}
                        <Badge color="blue">Preconfigured</Badge>
                      {/if}
                    </div>
                    <div class="flex items-center gap-2">
                      {#if !network.in_use && network.saved}
                        <Button 
                          size="xs"
                          color="red"
                          on:click={() => {
                            if (confirm(`Are you sure you want to forget "${network.ssid}"?`)) {
                              try {
                                fetch(
                                  `${API_V1_STR}/wifi/forget/${encodeURIComponent(network.ssid)}`, 
                                  { method: 'DELETE' }
                                )
                                .then(response => {
                                  if (!response.ok) throw new Error('Failed to forget network');
                                  return fetchNetworks(); // Refresh the networks list
                                })
                                .catch(error => {
                                  console.error('Error forgetting network:', error);
                                  alert('Failed to forget network');
                                });
                              } catch (error) {
                                console.error('Error forgetting network:', error);
                                alert('Failed to forget network');
                              }
                            }
                          }}
                        >
                          Forget
                        </Button>
                      {/if}
                      {#if !network.in_use}
                        <Button 
                          size="xs"
                          on:click={() => network.ssid === preconfiguredSSID 
                            ? connectToPreconfigured() 
                            : connectToNetwork(network)}
                          disabled={connecting}
                        >
                          {connecting ? 'Connecting...' : 'Connect'}
                        </Button>
                      {/if}
                    </div>
                  </div>
                </Card>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Other Networks Section -->
        <div>
          <h2 class="text-lg font-semibold mb-3">Available Networks</h2>
          <div class="grid gap-4">
            {#each otherNetworks as network}
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
                    {#if network.ssid === preconfiguredSSID}
                      <Badge color="blue">Preconfigured</Badge>
                    {/if}
                  </div>
                  <div class="text-gray-400">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              </Card>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div> 