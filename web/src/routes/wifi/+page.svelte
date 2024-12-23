<script lang="ts">
  import { currentMode } from '$lib/stores/mode';
  import ClientWifi from '$lib/components/ClientWifi.svelte';
  import APWifi from '$lib/components/APWifi.svelte';

  // Add debug logging
  $: console.log('WiFi page - Current mode:', $currentMode);
</script>

<div class="container mx-auto p-4 max-w-2xl">
  <ClientWifi hideInAP={true} />
  <APWifi hideInClient={true} />
</div> 