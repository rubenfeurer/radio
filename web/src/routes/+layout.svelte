<script lang="ts">
  import "../app.css";
  import { onMount } from 'svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import { page } from '$app/stores';
  import { ws as wsStore } from '$lib/stores/websocket';
  import { currentMode } from '$lib/stores/mode';

  // Dynamically set the page title based on the current route
  $: title = {
    '/': 'Radio',
    '/monitor': 'System Monitor',
    '/wifi': 'WiFi Settings',
    '/stations': 'Choose Station'
  }[$page.url.pathname] || 'Radio';

  onMount(() => {
    wsStore.sendMessage({ type: "status_request" });
    currentMode.subscribe((mode) => {
      console.log('Mode changed in layout:', mode);
    });
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
