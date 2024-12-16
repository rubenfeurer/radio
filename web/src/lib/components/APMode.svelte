<script lang="ts">
  import { Card, Button, Badge, Input } from 'flowbite-svelte';
  import type { WiFiNetwork, CurrentConnection } from '$lib/types';
  import { Icons, getWifiIcon } from '$lib/icons';
  
  export let API_BASE: string;
  export let networks: WiFiNetwork[] = [];
  export let loading = false;
  export let connecting = false;
  export let selectedNetwork: WiFiNetwork | null = null;
  export let password = '';
  export let error: string | null = null;
  
  async function scanNetworks() {
    loading = true;
    error = null;
    try {
      const response = await fetch(`${API_BASE}/api/v1/wifi/scan`, {
        method: 'POST'
      });
      if (!response.ok) throw new Error('Failed to scan networks');
      const data = await response.json();
      networks = data.networks;
      networks.sort((a, b) => b.signal_strength - a.signal_strength);
    } catch (err) {
      console.error('Error scanning networks:', err);
      error = 'Failed to scan networks';
    } finally {
      loading = false;
    }
  }

  async function attemptConnection(ssid: string, password: string) {
    connecting = true;
    error = null;
    try {
      // First verify we're in AP mode (case-insensitive check)
      const modeResponse = await fetch(`${API_BASE}/api/v1/wifi/mode`);
      const { mode } = await modeResponse.json();
      
      if (mode.toLowerCase() !== 'ap') {
        throw new Error('Not in AP mode');
      }
      
      // Attempt connection
      const response = await fetch(`${API_BASE}/api/v1/wifi/ap/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ssid, password })
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Connection error details:', errorData);
        throw new Error(errorData.detail || 'Failed to connect');
      }
      
      // Wait longer for mode switch and connection (30 seconds)
      await new Promise(resolve => setTimeout(resolve, 30000));
      
      // Only redirect on success
      window.location.href = 'http://192.168.4.1';
      
    } catch (err) {
      console.error('Connection error:', err);
      error = err.message || 'Failed to connect to network';
      // Don't clear form or rescan on error
    } finally {
      connecting = false;
    }
  }

  // Initial network scan
  scanNetworks();
</script>

<div class="grid gap-6 w-full">
  <div class="flex justify-between items-center">
    <h1 class="text-2xl font-bold">WiFi Settings (AP Mode)</h1>
    <Button 
      size="sm"
      disabled={loading}
      on:click={scanNetworks}
    >
      <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
      </svg>
      {loading ? 'Scanning...' : 'Scan Networks'}
    </Button>
  </div>

  {#if error}
    <div class="p-4 text-red-500 bg-red-100 rounded-lg">
      {error}
    </div>
  {/if}

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
          <Button color="alternative" on:click={() => {
            selectedNetwork = null;
            password = '';
            error = null;
          }}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  {:else}
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
      <div class="grid gap-4">
        {#each networks as network}
          <Card 
            class="w-full cursor-pointer hover:bg-gray-50 transition-colors"
            on:click={() => {
              error = null;
              if (network.security) {
                selectedNetwork = network;
              } else {
                attemptConnection(network.ssid, '');
              }
            }}
          >
            <div class="flex items-center justify-between p-1">
              <div class="flex items-center gap-3">
                {@html getWifiIcon(network.signal_strength)}
                <span class="font-semibold">{network.ssid}</span>
                {#if network.security}
                  {@html Icons.lock}
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
    {/if}
  {/if}
</div> 