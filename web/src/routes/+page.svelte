<script lang="ts">
  import RadioStations from '$lib/components/RadioStations.svelte';
  import VolumeControl from '$lib/components/VolumeControl.svelte';
  import WiFiStatus from '$lib/components/WiFiStatus.svelte';
  import MonitorCard from '$lib/components/MonitorCard.svelte';
  import ModeControl from '$lib/components/ModeControl.svelte';
</script>

<div class="flex flex-col gap-4">
  <RadioStations />
  <VolumeControl />
  <WiFiStatus />
  <MonitorCard />
  <ModeControl />
</div>