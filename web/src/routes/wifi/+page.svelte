<script lang="ts">
  import { currentMode } from '$lib/stores/mode';
  import ClientWifi from '$lib/components/ClientWifi.svelte';
  import APWifi from '$lib/components/APWifi.svelte';
</script>

<div class="container mx-auto p-4 max-w-2xl">
  {#if $currentMode === 'ap'}
    <APWifi />
  {:else}
    <ClientWifi />
  {/if}
</div> 