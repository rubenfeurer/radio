<script lang="ts">
  import "../app.css";
  import { onMount, onDestroy } from 'svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import { page } from '$app/stores';
  import { ws as wsStore, websocketStore } from '$lib/stores/websocket';
  import { currentMode } from '$lib/stores/mode';

  // Dynamically set the page title based on the current route
  $: title = {
    '/': 'Radio',
    '/monitor': 'System Monitor',
    '/wifi': 'WiFi Settings',
    '/stations': 'Choose Station'
  }[$page.url.pathname] || 'Radio';

  let updateInterval: ReturnType<typeof setInterval>;

  // Watch for WebSocket messages
  $: if ($websocketStore.data) {
    const message = $websocketStore.data;
    console.log('Layout received message:', message.type);
    
    // Handle different message types
    switch (message.type) {
      case 'status_update':
        // Handle status updates
        break;
    }
  }

  onMount(() => {
    // Initial status request
    if ($wsStore?.readyState === WebSocket.OPEN) {
      wsStore.sendMessage({ type: "status_request" });
    }

    // Set up periodic status updates
    updateInterval = setInterval(() => {
      if ($wsStore?.readyState === WebSocket.OPEN) {
        wsStore.sendMessage({ type: "status_request" });
      }
    }, 5000);
  });

  onDestroy(() => {
    if (updateInterval) clearInterval(updateInterval);
  });
</script>

<svelte:head>
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="0">
  <title>{title}</title>
</svelte:head>

<div class="min-h-screen bg-gray-50">
  <div class="max-w-4xl mx-auto p-4">
    <PageHeader {title} />
    <slot />
  </div>
</div>
