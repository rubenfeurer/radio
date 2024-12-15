<script lang="ts">
  import { onMount } from 'svelte';
  import { Button, Badge } from 'flowbite-svelte';
  import { browser } from '$app/environment';
  import APMode from '$lib/components/APMode.svelte';
  import ClientMode from '$lib/components/ClientMode.svelte';
  import { Icons } from '$lib/icons';
  import type { NetworkStatus } from '$lib/types';
  
  // Get the current hostname (IP or domain)
  const currentHost = browser ? window.location.hostname : '';
  
  // Determine API base URL
  const API_BASE = browser 
    ? (window.location.port === '5173' 
      ? `http://${currentHost}:80`
      : '')
    : '';

  let currentMode = 'CLIENT';
  let loading = true;

  async function checkMode() {
    try {
      const response = await fetch(`${API_BASE}/api/v1/wifi/mode`);
      if (!response.ok) throw new Error('Failed to fetch mode');
      const data = await response.json();
      currentMode = data.mode.toUpperCase();
    } catch (error) {
      console.error('Error fetching mode:', error);
      currentMode = 'CLIENT'; // Default to CLIENT mode on error
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    if (browser) {
      checkMode();
    }
  });
</script>

<div class="container mx-auto p-4 max-w-2xl">
  <a href="/" class="inline-block mb-4">
    <Button color="alternative">
      {@html Icons.arrowLeft}
      <span class="ml-2">Back</span>
    </Button>
  </a>

  <div class="mb-4">
    <Badge color={currentMode === 'AP' ? 'purple' : 'blue'}>
      {currentMode} Mode
    </Badge>
  </div>

  {#if loading}
    <div class="animate-pulse">
      <div class="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
      <div class="h-4 bg-gray-200 rounded w-1/2"></div>
    </div>
  {:else}
    {#if currentMode === 'AP'}
      <APMode {API_BASE} />
    {:else}
      <ClientMode {API_BASE} />
    {/if}
  {/if}
</div> 