<script lang="ts">
  import { onMount } from 'svelte';
  import { Card, Button, Badge, Input } from 'flowbite-svelte';
  import { goto } from '$app/navigation';

  // SVG icons
  const Icons = {
    arrowLeft: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
    </svg>`,
    wifi: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
    </svg>`,
    lock: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
    </svg>`
  };

  let networks: WiFiNetwork[] = [];
  let selectedNetwork: WiFiNetwork | null = null;
  let password = '';
  let connecting = false;

  onMount(async () => {
    await fetchNetworks();
  });

  async function fetchNetworks() {
    try {
      const response = await fetch('/api/v1/wifi/networks');
      if (!response.ok) throw new Error('Failed to fetch networks');
      networks = await response.json();
    } catch (error) {
      console.error('Error fetching networks:', error);
    }
  }

  async function connectToNetwork(network: WiFiNetwork) {
    if (!network.security) {
      // Connect without password
      await attemptConnection(network.ssid, '');
    } else {
      selectedNetwork = network;
    }
  }

  async function attemptConnection(ssid: string, password: string) {
    connecting = true;
    try {
      const response = await fetch('/api/v1/wifi/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ssid, password })
      });

      if (!response.ok) throw new Error('Failed to connect');
      
      // Success - go back to main page
      goto('/');
    } catch (error) {
      console.error('Connection error:', error);
      alert('Failed to connect to network');
    } finally {
      connecting = false;
    }
  }
</script>

<div class="container mx-auto p-4 max-w-2xl">
  <a href="/" class="inline-block mb-4">
    <Button color="alternative">
      {@html Icons.arrowLeft}
      <span class="ml-2">Back</span>
    </Button>
  </a>

  <h1 class="text-2xl font-bold mb-4">WiFi Settings</h1>

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
    <div class="grid gap-4 w-full">
      {#each networks as network}
        <Card class="w-full">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              {@html Icons.wifi}
              <span class="font-semibold">{network.ssid}</span>
              {#if network.security}
                {@html Icons.lock}
              {/if}
            </div>
            <Button on:click={() => connectToNetwork(network)}>
              Connect
            </Button>
          </div>
        </Card>
      {/each}
    </div>
  {/if}
</div> 