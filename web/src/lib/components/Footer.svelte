<script lang="ts">
  import { Badge } from 'flowbite-svelte';
  import { ws } from '$lib/stores/websocket';
  import { currentMode } from '$lib/stores/mode';

  // WebSocket connection state
  let wsConnected = false;
  ws.subscribe(socket => {
    wsConnected = socket !== null;
  });

  // Helper for mode badge color
  $: modeBadgeColor = $currentMode === 'ap' ? 'purple' : 'blue';
  $: modeText = $currentMode === undefined ? 'Loading...' : $currentMode?.toUpperCase();
</script>

<footer class="bg-white border-t border-gray-200 p-4 mt-8">
  <div class="max-w-4xl mx-auto flex justify-end gap-2">
    <Badge color={modeBadgeColor}>
      {modeText}
    </Badge>
    <Badge color={wsConnected ? "green" : "red"}>
      {wsConnected ? "Connected" : "Disconnected"}
    </Badge>
  </div>
</footer> 