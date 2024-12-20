<script lang="ts">
  import { Card, Range } from 'flowbite-svelte';
  import { onMount } from 'svelte';
  import { currentMode } from '$lib/stores/mode';
  import { ws } from '$lib/stores/websocket';
  import { API_V1_STR } from '$lib/config';  // Import API_V1_STR

  export let hideInAP = false;
  let volume = 70;  // Initialize with default value
  let error: string | null = null;

  // Fetch initial volume from REST API
  async function fetchVolume() {
    try {
      const response = await fetch('/api/v1/volume');
      if (!response.ok) {
        throw new Error('Failed to fetch volume');
      }
      const data = await response.json();
      volume = data.volume;
    } catch (error) {
      console.error("Failed to fetch initial volume:", error);
      error = "Failed to fetch volume";
    }
  }

  onMount(() => {
    fetchVolume();
  });

  // Listen for WebSocket volume updates
  ws.subscribe(socket => {
    if (socket) {
      console.log('WebSocket connected in VolumeControl');
      socket.addEventListener('message', (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message received in VolumeControl:', data);
          
          // Check for both volume_update and status_update types
          if (data.type === 'volume_update') {
            console.log('Updating volume to:', data.volume);
            volume = data.volume;
          } else if (data.type === 'status_update' && data.data?.volume !== undefined) {
            console.log('Updating volume from status to:', data.data.volume);
            volume = data.data.volume;
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      });
    }
  });

  async function updateVolume(event: CustomEvent) {
    const newVolume = parseInt(event.target.value);
    try {
      const response = await fetch(`${API_V1_STR}/volume`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ volume: newVolume }),
      });

      if (!response.ok) {
        throw new Error('Failed to update volume');
      }

      volume = newVolume;
      error = null;
    } catch (error) {
      console.error("Failed to update volume:", error);
      error = "Failed to update volume";
    }
  }
</script>

{#if !hideInAP || $currentMode !== 'ap'}
  <Card>
    <div class="flex flex-col gap-2">
      <h3 class="text-lg font-semibold">Volume Control</h3>
      {#if error}
        <p class="text-red-500 text-sm">{error}</p>
      {/if}
      <div class="flex items-center gap-4">
        <span class="text-sm w-8">{volume}%</span>
        <Range 
          min={0} 
          max={100} 
          value={volume}
          on:change={updateVolume}
          class="flex-1"
        />
      </div>
    </div>
  </Card>
{/if} 