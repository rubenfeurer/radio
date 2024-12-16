<script lang="ts">
    import { onMount } from 'svelte';
    import { Card, Button } from 'flowbite-svelte';
    import type { NetworkStatus } from '$lib/types';
    
    export let API_BASE: string;
    let status: NetworkStatus | null = null;
    let loading = true;
    let error: string | null = null;
  
    async function fetchStatus() {
      loading = true;
      error = null;
      try {
        const response = await fetch(`${API_BASE}/api/v1/network/status`);
        if (!response.ok) throw new Error('Failed to fetch network status');
        status = await response.json();
      } catch (err) {
        console.error('Error fetching network status:', err);
        error = 'Failed to fetch network status';
      } finally {
        loading = false;
      }
    }
  
    onMount(() => {
      fetchStatus();
    });
  </script>
  
  <div class="grid gap-6">
    <div class="flex justify-between items-center">
      <h2 class="text-xl font-bold">Network Status</h2>
      <Button 
        size="sm"
        disabled={loading}
        on:click={fetchStatus}
      >
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
        Refresh
      </Button>
    </div>
  
    {#if error}
      <div class="p-4 text-red-500 bg-red-100 rounded-lg">
        {error}
      </div>
    {/if}
  
    {#if loading}
      <Card>
        <div class="animate-pulse">
          <div class="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div class="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
      </Card>
    {:else if status}
      <Card>
        <div class="grid gap-4">
          <div>
            <span class="font-semibold">IP Address:</span>
            <span>{status.ip_address || 'Not available'}</span>
          </div>
          <div>
            <span class="font-semibold">Hostname:</span>
            <span>{status.hostname}</span>
          </div>
          <div>
            <span class="font-semibold">WiFi SSID:</span>
            <span>{status.wifi_ssid || 'Not connected'}</span>
          </div>
          <div>
            <span class="font-semibold">Signal Strength:</span>
            <span>{status.signal_strength ? `${status.signal_strength}%` : 'N/A'}</span>
          </div>
          <div>
            <span class="font-semibold">Internet:</span>
            <span class={status.internet_connected ? 'text-green-500' : 'text-red-500'}>
              {status.internet_connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </Card>
    {/if}
  </div>