<script lang="ts">
  import { onMount } from 'svelte';
  import { Card, Button, Badge, Input } from 'flowbite-svelte';
  import type { WiFiNetwork, CurrentConnection } from '$lib/types';
  import { Icons, getWifiIcon } from '$lib/icons';
  
  export let API_BASE: string;
  export let networks: WiFiNetwork[] = [];
  export let savedNetworks: WiFiNetwork[] = [];
  export let otherNetworks: WiFiNetwork[] = [];
  export let currentConnection: CurrentConnection | null = null;
  export let selectedNetwork: WiFiNetwork | null = null;
  export let password = '';
  export let connecting = false;
  export let loading = false;
  export let preconfiguredSSID: string | null = null;

  async function fetchNetworks() {
    loading = true;
    try {
      const response = await fetch(`${API_BASE}/api/v1/wifi/network_status`);
      if (!response.ok) throw new Error('Failed to fetch networks');
      const data = await response.json();
      
      networks = data.wifi_status.available_networks.filter(network => 
        network.ssid && network.ssid.trim() !== ''
      );
      preconfiguredSSID = data.wifi_status.preconfigured_ssid;
      currentConnection = {
        ssid: data.wifi_status.ssid,
        is_connected: data.wifi_status.is_connected
      };
      
      networks.sort((a, b) => b.signal_strength - a.signal_strength);
      savedNetworks = networks.filter(n => n.saved || n.in_use);
      otherNetworks = networks.filter(n => !n.saved && !n.in_use);
      
    } catch (error) {
      console.error('Error fetching networks:', error);
    } finally {
      loading = false;
    }
  }

  async function connectToNetwork(network: WiFiNetwork) {
    if (network.security) {
      selectedNetwork = network;
    } else {
      await attemptConnection(network.ssid, '');
    }
  }

  async function connectToPreconfigured() {
    if (!preconfiguredSSID) return;
    connecting = true;
    try {
      const response = await fetch(`${API_BASE}/api/v1/wifi/connect/preconfigured`, {
        method: 'POST'
      });
      if (!response.ok) throw new Error('Failed to connect to preconfigured network');
      await fetchNetworks();
    } catch (error) {
      console.error('Error connecting to preconfigured network:', error);
      alert('Failed to connect to preconfigured network');
    } finally {
      connecting = false;
    }
  }

  async function attemptConnection(ssid: string, password: string) {
    connecting = true;
    try {
        console.log(`Attempting to connect to ${ssid}...`);
        
        const response = await fetch(`${API_BASE}/api/v1/wifi/connect`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ssid, password })
        });

        if (!response.ok) {
            const errorData = await response.json();
            console.error('Connection error details:', errorData);
            throw new Error(errorData.detail || 'Failed to connect');
        }

        // Add delay to allow connection to establish
        console.log('Connection successful, waiting for network to stabilize...');
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        console.log('Refreshing network list...');
        await fetchNetworks();
        selectedNetwork = null;
        password = '';
        
    } catch (error: any) {
        console.error('Connection error:', error);
        alert(error.message || 'Failed to connect to network');
    } finally {
        connecting = false;
    }
  }

  onMount(() => {
    fetchNetworks();
  });
</script>

<div class="grid gap-6 w-full">
  <div class="flex justify-between items-center">
    <h1 class="text-2xl font-bold">WiFi Settings (Client Mode)</h1>
  </div>

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
              <Card class="w-full">
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
                  <div class="flex gap-2">
                    <Button 
                      size="xs"
                      color="red"
                      on:click={() => {
                        if (confirm(`Forget network "${network.ssid}"?`)) {
                          fetch(
                            `${API_BASE}/api/v1/wifi/forget/${encodeURIComponent(network.ssid)}`,
                            { method: 'DELETE' }
                          )
                          .then(() => fetchNetworks())
                          .catch(error => {
                            console.error('Error:', error);
                            alert('Failed to forget network');
                          });
                        }
                      }}
                    >
                      Forget
                    </Button>
                    {#if !network.in_use}
                      <Button 
                        size="xs"
                        on:click={() => network.ssid === preconfiguredSSID 
                          ? connectToPreconfigured() 
                          : attemptConnection(network.ssid, '')}
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
  {/if}
</div> 