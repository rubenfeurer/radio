<script lang="ts">
  import { onMount } from 'svelte';
  import { Card, Input, Button, Badge, Spinner } from 'flowbite-svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import type { RadioStation } from '../../types';

  let allStations: RadioStation[] = [];
  let searchQuery = '';
  let filteredStations: RadioStation[] = [];
  let targetSlot: number | null = null;
  let isLoading = true;
  
  // Pagination
  let currentPage = 0;
  const itemsPerPage = 12;
  let displayedStations: RadioStation[] = [];

  onMount(async () => {
    const slotParam = $page.url.searchParams.get('slot');
    targetSlot = slotParam ? parseInt(slotParam) : null;

    try {
        const response = await fetch(`/api/v1/stations`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const stations = await response.json();
        allStations = stations.sort((a, b) => a.name.localeCompare(b.name));
        updateFilteredStations();
    } catch (error) {
        console.error('Error loading stations:', error);
    } finally {
        isLoading = false;
    }
  });

  function updateFilteredStations() {
    if (!searchQuery) {
      filteredStations = allStations.sort((a, b) => a.name.localeCompare(b.name));
    } else {
      const query = searchQuery.toLowerCase();
      filteredStations = allStations
        .filter(station =>
          station.name.toLowerCase().includes(query) ||
          station.country?.toLowerCase().includes(query) ||
          station.location?.toLowerCase().includes(query)
        )
        .sort((a, b) => a.name.localeCompare(b.name));
    }
    updateDisplayedStations();
  }

  function updateDisplayedStations() {
    const start = currentPage * itemsPerPage;
    displayedStations = filteredStations.slice(start, start + itemsPerPage);
  }

  function searchStations() {
    currentPage = 0;
    updateFilteredStations();
  }

  function nextPage() {
    if ((currentPage + 1) * itemsPerPage < filteredStations.length) {
      currentPage++;
      updateDisplayedStations();
    }
  }

  function previousPage() {
    if (currentPage > 0) {
      currentPage--;
      updateDisplayedStations();
    }
  }

  async function assignStationToSlot(station: RadioStation) {
    if (!targetSlot) return;

    try {
        console.log('Assigning station:', station);
        const response = await fetch(`/api/v1/stations/${targetSlot}/assign`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                stationId: station.id,
                name: station.name,
                url: station.url,
                country: station.country || null,
                location: station.location || null
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            console.error('Server error:', errorData);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        goto('/');
    } catch (error) {
        console.error("Failed to assign station:", error);
    }
  }
</script>

<div class="max-w-4xl mx-auto p-4">
  <div class="mb-6">
    <Button 
      color="alternative" 
      class="mb-4"
      on:click={() => goto('/')}
    >
      <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
      </svg>
      Back
    </Button>

    <div class="flex justify-between items-center">
      <h1 class="text-2xl font-bold">Radio Stations</h1>
      {#if targetSlot}
        <Badge color="blue">Selecting for Slot {targetSlot}</Badge>
      {/if}
    </div>
  </div>

  <Input
    placeholder="Search for Station, Country or Location..."
    bind:value={searchQuery}
    on:input={searchStations}
    class="mb-4"
  />

  <div class="grid gap-4 md:grid-cols-3">
    {#if isLoading}
      <div class="flex items-center">
        <Spinner />
      </div>
    {:else}
      {#each displayedStations as station}
        <Card padding="xl">
          <h5 class="text-xl font-bold">{station.name}</h5>
          <p class="text-gray-700">Country: {station.country || 'N/A'}</p>
          <p class="text-gray-700">Location: {station.location || 'N/A'}</p>
          <Button 
            color="primary"
            class="mt-4"
            on:click={() => assignStationToSlot(station)}
          >
            Select
          </Button>
        </Card>
      {/each}
    {/if}
  </div>

  {#if filteredStations.length > itemsPerPage}
    <div class="flex justify-center gap-4 mt-6">
      <Button 
        color="alternative"
        on:click={previousPage}
        disabled={currentPage === 0}
      >
        Previous
      </Button>
      <span class="py-2">
        Page {currentPage + 1} of {Math.ceil(filteredStations.length / itemsPerPage)}
      </span>
      <Button 
        color="alternative"
        on:click={nextPage}
        disabled={(currentPage + 1) * itemsPerPage >= filteredStations.length}
      >
        Next
      </Button>
    </div>
  {/if}

  <div class="text-center text-gray-600 mt-4">
    Showing {displayedStations.length} of {filteredStations.length} stations
  </div>
</div> 