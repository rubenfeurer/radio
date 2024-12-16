<script lang="ts">
  import { Card, Range } from 'flowbite-svelte';
  import { browser } from '$app/environment';
  import { onMount } from 'svelte';

  export let volume: number;

  const currentHost = browser ? window.location.hostname : '';
  const API_BASE = browser 
    ? (window.location.port === '5173' 
      ? `http://${currentHost}:80`
      : '')
    : '';

  onMount(async () => {
    await fetchVolume();
  });

  async function fetchVolume() {
    try {
      const response = await fetch(`${API_BASE}/api/v1/volume`);
      const data = await response.json();
      volume = data.volume;
    } catch (error) {
      console.error("Failed to fetch volume:", error);
    }
  }

  async function updateVolume(event: CustomEvent) {
    // Convert to integer since Range might send float
    const newVolume = Math.round(Number(event.target.value));
    
    try {
      const response = await fetch(`${API_BASE}/api/v1/volume`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ volume: newVolume })
      });

      if (!response.ok) {
        const error = await response.json();
        console.error("Volume update failed:", error);
        return;
      }

      volume = newVolume;
    } catch (error) {
      console.error("Failed to update volume:", error);
    }
  }
</script>

<Card class="mb-4">
  <div class="flex flex-col gap-2">
    <h3 class="text-lg font-semibold">Volume Control</h3>
    <div class="flex items-center gap-4">
      <span class="text-sm w-8">{volume}%</span>
      <Range 
        min={0} 
        max={100} 
        bind:value={volume}
        on:change={updateVolume}
        class="flex-1"
      />
    </div>
  </div>
</Card> 