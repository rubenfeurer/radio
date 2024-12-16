<!-- web/src/lib/components/ModeSwitch.svelte -->
<script lang="ts">
  import { Card, Button, Badge } from 'flowbite-svelte';
  import { networkMode } from '$lib/stores/network';
  
  export let API_BASE: string;
  export let ws: WebSocket | null = null;

  let currentMode = 'CLIENT';
  let isSwitching = false;

  // Subscribe to network mode store
  networkMode.subscribe(value => {
    if (value) {
      currentMode = value.mode;
      isSwitching = value.is_switching;
    }
  });

  async function toggleMode() {
    try {
      networkMode.set({
        mode: currentMode,
        is_switching: true
      });
      
      // First notify through WebSocket if in client mode
      if (currentMode === 'CLIENT' && ws) {
        ws.send(JSON.stringify({ 
          type: 'mode_change',
          data: { mode: 'AP' }
        }));
      }
      
      const response = await fetch(`${API_BASE}/api/v1/wifi/mode/toggle`, {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error('Failed to switch mode');
      }

      if (currentMode === 'CLIENT') {
        setTimeout(() => {
          window.location.href = 'http://192.168.4.1';
        }, 5000);
      }
      
    } catch (error) {
      console.error('Error switching mode:', error);
      alert('Failed to switch mode. Please try again.');
      networkMode.set({
        mode: currentMode,
        is_switching: false
      });
    }
  }
</script>

<Card class="mt-4">
  <div class="flex flex-col gap-2">
    <h3 class="text-lg font-semibold">Network Mode</h3>
    <div class="flex items-center justify-between">
      <div>
        {#if isSwitching}
          <Badge color="yellow" class="ml-2">Switching...</Badge>
        {/if}
      </div>
      <Button
        disabled={isSwitching}
        on:click={toggleMode}
        class="w-full"
      >
        Switch Mode
      </Button>
    </div>
  </div>
</Card>