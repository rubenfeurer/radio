<script lang="ts">
  import { Card, Button, Badge, Input, Alert } from 'flowbite-svelte';
  import { browser } from '$app/environment';
  import { onMount } from 'svelte';
  import { ws } from '$lib/stores/websocket';
  import { currentMode } from '$lib/stores/mode';
  import { API_V1_STR } from '$lib/config';

  // Show only in AP mode, and hide when mode is undefined
  $: shouldHide = !$currentMode || $currentMode !== 'ap';
  
  // Debug logging
  $: {
    console.log('APWifi - Current mode:', $currentMode);
    console.log('APWifi - Should hide:', shouldHide);
  }

  interface WiFiNetwork {
    ssid: string;
    security: string | null;
    signal_strength: number;
    in_use: boolean;
    saved: boolean;
  }

  interface APStatus {
    is_ap_mode: boolean;
    ap_ssid: string;
    available_networks: WiFiNetwork[];
    saved_networks: WiFiNetwork[];
    preconfigured_ssid: string | null;
  }

  let networks: WiFiNetwork[] = [];
  let savedNetworks: WiFiNetwork[] = [];
  let otherNetworks: WiFiNetwork[] = [];
  let selectedNetwork: WiFiNetwork | null = null;
  let password = '';
  let connecting = false;
  let error: string | null = null;
  let apStatus: APStatus | null = null;
  let connectionAdded = false;

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
    return Icons.wifiStrong;
  }

  onMount(async () => {
    await fetchNetworks();
    // Subscribe to WebSocket updates
    ws.subscribe(socket => {
      if (socket) {
        socket.addEventListener('message', handleWebSocketMessage);
      }
    });
  });

  async function fetchNetworks() {
    try {
      const response = await fetch(`${API_V1_STR}/ap/networks`);
      if (!response.ok) throw new Error('Failed to fetch networks');
      const data = await response.json();
      networks = data.available_networks || [];
      
      // Sort networks by signal strength
      networks.sort((a, b) => b.signal_strength - a.signal_strength);
      
      // Split networks into saved and other
      savedNetworks = networks.filter(n => n.saved || n.ssid === data.preconfigured_ssid);
      otherNetworks = networks.filter(n => !n.saved && n.ssid !== data.preconfigured_ssid);
      
      apStatus = {
        is_ap_mode: true,
        ap_ssid: "RadioAP",
        available_networks: networks,
        saved_networks: savedNetworks,
        preconfigured_ssid: data.preconfigured_ssid
      };
    } catch (e) {
      console.error('Error fetching networks:', e);
      error = 'Failed to fetch networks';
    }
  }

  function handleWebSocketMessage(event: MessageEvent) {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'mode_update') {
        // Update the mode store with lowercase value
        currentMode.set(data.mode.toLowerCase());
        
        if (data.mode === 'client') {
          // Handle client mode switch
          setTimeout(() => {
            if ('caches' in window) {
              caches.keys().then((names) => {
                names.forEach(name => {
                  caches.delete(name);
                });
              });
            }
            window.location.replace(`http://${window.location.hostname}:5173/?nocache=${Date.now()}`);
          }, 2000);
        }
      }
    } catch (e) {
      console.error('Error handling WebSocket message:', e);
    }
  }

  async function connectToNetwork(network: WiFiNetwork) {
    if (network.security) {
        selectedNetwork = network;
    } else {
        // For open networks
        if (network.saved || network.ssid === apStatus?.preconfigured_ssid) {
            await modifyConnection(network.ssid, '');
        } else {
            await addConnection(network.ssid, '');
        }
    }
  }

  async function modifyConnection(ssid: string, password: string) {
    connecting = true;
    error = null;
    connectionAdded = false;
    
    try {
        const response = await fetch(`${API_V1_STR}/ap/modifyconnection`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                ssid, 
                password,
                priority: 1 // Default priority
            })
        });

        const data = await response.json();
        
        if (!response.ok) {
            console.error('Modification error:', data);
            error = data.detail || "Failed to modify network connection";
            return;
        }

        // Success
        connectionAdded = true;
        error = "Network connection modified successfully!";
        selectedNetwork = null;
        password = '';
        await fetchNetworks(); // Refresh network list
        
    } catch (e) {
        console.error('Modification error:', e);
        error = "Failed to modify network connection";
    } finally {
        connecting = false;
    }
  }

  async function addConnection(ssid: string, password: string) {
    connecting = true;
    error = null;
    connectionAdded = false;
    
    try {
        const response = await fetch(`${API_V1_STR}/ap/addconnection`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              ssid, 
              password,
              priority: 1 // Default priority
            })
        });

        const data = await response.json();
        
        if (!response.ok) {
            console.error('Connection error:', data);
            error = data.detail || "Failed to save network connection";
            return;
        }

        // Success
        connectionAdded = true;
        error = "Network connection saved successfully!";
        selectedNetwork = null;
        password = '';
        await fetchNetworks(); // Refresh network list
        
    } catch (e) {
        console.error('Connection error:', e);
        error = "Failed to save network connection";
    } finally {
        connecting = false;
    }
  }

  async function switchToClientMode() {
    try {
      const response = await fetch(`${API_V1_STR}/mode/client`, {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error('Failed to switch to client mode');
      }

      error = "Switching to client mode... Please wait.";
    } catch (e) {
      console.error('Mode switch error:', e);
      error = "Failed to switch to client mode";
    }
  }
</script>

{#if !shouldHide}
  <div class="container mx-auto p-4 max-w-2xl">
    <h1 class="text-2xl font-bold mb-4">Networks (AP Mode)</h1>
    
    <div class="mb-4">
      {#if apStatus?.ap_ssid}
        <Alert color="info">
          Connected to Access Point: {apStatus.ap_ssid}
        </Alert>
      {/if}
    </div>

    {#if error}
      <Alert color={connectionAdded ? "green" : "red"} class="mb-4">
        {error}
      </Alert>
    {/if}

    {#if connectionAdded}
      <Card class="mb-4">
        <div class="flex flex-col items-center gap-4">
          <p>Network connection saved successfully!</p>
          <Button color="blue" on:click={switchToClientMode}>
            Switch to Client Mode
          </Button>
        </div>
      </Card>
    {/if}

    {#if selectedNetwork}
      <Card class="mb-4">
        <h3 class="text-lg mb-4">
          {selectedNetwork.saved || selectedNetwork.ssid === apStatus?.preconfigured_ssid 
            ? 'Modify connection for' 
            : 'Add connection for'} {selectedNetwork.ssid}
        </h3>
        <form on:submit|preventDefault={() => {
          if (selectedNetwork.saved || selectedNetwork.ssid === apStatus?.preconfigured_ssid) {
            modifyConnection(selectedNetwork.ssid, password);
          } else {
            addConnection(selectedNetwork.ssid, password);
          }
        }}>
          <Input
            type="password"
            placeholder="Network password"
            bind:value={password}
            class="mb-4"
          />
          <div class="flex gap-2">
            <Button type="submit" disabled={connecting}>
              {connecting ? 'Saving...' : (selectedNetwork.saved || selectedNetwork.ssid === apStatus?.preconfigured_ssid 
                ? 'Modify Connection' 
                : 'Save Connection')}
            </Button>
            <Button color="alternative" on:click={() => selectedNetwork = null}>
              Cancel
            </Button>
          </div>
        </form>
      </Card>
    {:else}
      <!-- Saved Networks Section -->
      {#if savedNetworks.length > 0}
        <div class="mb-4">
          <h2 class="text-lg font-semibold mb-3">Saved Networks</h2>
          <div class="grid gap-4">
            {#each savedNetworks as network}
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
                    {#if network.saved}
                      <Badge color="green">Saved</Badge>
                    {/if}
                  </div>
                  <Badge color="dark">
                    {network.signal_strength}%
                  </Badge>
                </div>
              </Card>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Other Networks Section -->
      <div class="mb-4">
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
                </div>
                <Badge color="dark">
                  {network.signal_strength}%
                </Badge>
              </div>
            </Card>
          {/each}
        </div>
      </div>
    {/if}
  </div>
{/if} 