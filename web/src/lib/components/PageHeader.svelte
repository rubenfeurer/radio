<script lang="ts">
  import { page } from '$app/stores';
  import { Badge } from 'flowbite-svelte';
  import { ws } from '$lib/stores/websocket';
  import { currentMode } from '$lib/stores/mode';

  // Props
  export let title: string;

  // Get current path for back navigation
  $: currentPath = $page.url.pathname;
  $: parentPath = currentPath.split('/').slice(0, -1).join('/') || '/';
  $: showBackButton = currentPath !== '/';

  // WebSocket connection state
  let wsConnected = false;
  ws.subscribe(socket => {
    wsConnected = socket !== null;
  });

  // Helper for mode badge color
  $: modeBadgeColor = $currentMode === 'ap' ? 'purple' : 'blue';
  $: modeText = $currentMode === undefined ? 'Loading...' : $currentMode?.toUpperCase();
</script>

<div class="mb-6 flex justify-between items-center">
  <div class="flex items-center gap-4">
    {#if showBackButton}
      <a href={parentPath} class="text-gray-500 hover:text-gray-700">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
      </a>
    {/if}
    <h1 class="text-2xl font-bold">{title}</h1>
  </div>
  <div class="flex items-center gap-2">
    <Badge color={modeBadgeColor}>
      {modeText}
    </Badge>
    <Badge color={wsConnected ? "green" : "red"}>
      {wsConnected ? "Connected" : "Disconnected"}
    </Badge>
  </div>
</div> 