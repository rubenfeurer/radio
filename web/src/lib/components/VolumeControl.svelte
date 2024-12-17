<script lang="ts">
  import { Card, Range } from 'flowbite-svelte';
  import { browser } from '$app/environment';
  import { onMount } from 'svelte';
  import { currentMode } from '$lib/stores/mode';

  export let hideInAP = false;
  let volume = 70;  // Initialize with default value
  let error: string | null = null;

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
      if (!response.ok) {
        throw new Error('Failed to fetch volume');
      }
      const data = await response.json();
      volume = data.volume;
    } catch (error) {
      console.error("Failed to fetch volume:", error);
      error = "Failed to load volume";
    }
  }

  async function updateVolume(event: CustomEvent) {
    try {
      const newVolume = Math.round(Number(event.target.value));
      const response = await fetch(`${API_BASE}/api/v1/volume`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ volume: newVolume })
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