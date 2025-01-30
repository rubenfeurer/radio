<script lang="ts">
  import { onMount } from 'svelte';
  import { currentMode } from '$lib/stores/mode';
  import RadioStations from '$lib/components/RadioStations.svelte';
  import VolumeControl from '$lib/components/VolumeControl.svelte';
  import WiFiStatus from '$lib/components/WiFiStatus.svelte';
  import MonitorCard from '$lib/components/MonitorCard.svelte';
  import ModeControl from '$lib/components/ModeControl.svelte';

  let error: string | null = null;

  $: {
    console.log('Main page - Current mode:', $currentMode);
  }

  onMount(async () => {
    try {
      console.log('Main page mounted - Initial mode:', $currentMode);
      // Any initialization if needed
    } catch (err) {
      console.error("Page initialization error:", err);
      error = "Failed to initialize page";
    }
  });
</script>

<div class="flex flex-col gap-4">
  {#if error}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
      {error}
    </div>
  {/if}
  <RadioStations hideInAP={true} />
  <VolumeControl hideInAP={true} />
  <WiFiStatus />
  <MonitorCard />
  <ModeControl />
</div>