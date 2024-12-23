<script lang="ts">
  import { Card, Button, Badge } from 'flowbite-svelte';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { onMount } from 'svelte';
  import { ws } from '$lib/stores/websocket';
  import { currentMode } from '$lib/stores/mode';
  import { API_V1_STR } from '$lib/config';  // Import API_V1_STR

  // Types
  interface RadioStation {
    name: string;
    url: string;
    slot: number;
    country?: string | null;
    location?: string | null;
  }

  let stations: RadioStation[] = [];
  let currentPlayingSlot: number | null = null;
  export let hideInAP = false;
  let error: string | null = null;

  // Subscribe to WebSocket and handle messages
  ws.subscribe(socket => {
    if (socket) {
      socket.addEventListener('message', (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message received:', data);

          if (data.type === 'status_response' || data.type === 'status_update') {
            console.log('Previous playing slot:', currentPlayingSlot);
            console.log('Status data:', {
              current_station: data.data.current_station,
              is_playing: data.data.is_playing
            });

            if (data.data.is_playing) {
              currentPlayingSlot = typeof data.data.current_station === 'object' 
                ? data.data.current_station.slot 
                : data.data.current_station;
            } else {
              currentPlayingSlot = null;
            }

            console.log('Updated playing slot:', currentPlayingSlot);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      });

      socket.addEventListener('open', () => {
        console.log('WebSocket connected, requesting initial status');
        ws.sendMessage({ type: "status_request" });
      });
    }
  });

  onMount(async () => {
    try {
      console.log('Component mounted, requesting initial status');
      ws.sendMessage({ type: "status_request" });
      await loadInitialStations();
    } catch (err) {
      console.error("Failed to initialize:", err);
      error = "Failed to load stations";
    }
  });

  export async function loadInitialStations() {
    try {
        console.log("Fetching assigned stations...");
        const assignedResponse = await fetch(`${API_V1_STR}/stations/assigned`);
        console.log("Response status:", assignedResponse.status);
        
        if (!assignedResponse.ok) {
            const errorText = await assignedResponse.text();
            console.error("Error response:", errorText);
            throw new Error(`HTTP error! status: ${assignedResponse.status}`);
        }
        
        const assignedStations = await assignedResponse.json();
        console.log("Assigned stations:", assignedStations);
        
        const slots = [1, 2, 3];
        stations = []; // Reset stations array before loading

        for (const slot of slots) {
            try {
                if (assignedStations[slot] && assignedStations[slot] !== null) {
                    stations = [...stations, {
                        ...assignedStations[slot],
                        slot: parseInt(slot)
                    }];
                } else {
                    stations = [...stations, {
                        name: 'No station assigned',
                        url: '',
                        slot: parseInt(slot)
                    }];
                }
            } catch (error) {
                console.error(`Failed to fetch station ${slot}:`, error);
            }
        }
    } catch (error) {
        console.error("Failed to fetch stations:", error);
    }
  }

  async function toggleStation(slot: number) {
    try {
      const response = await fetch(`${API_V1_STR}/stations/${slot}/toggle`, {
        method: 'POST'
      });
      const data = await response.json();
      if (data.status === 'playing') {
        currentPlayingSlot = slot;
      } else {
        currentPlayingSlot = null;
      }
    } catch (error) {
      console.error("Failed to toggle station:", error);
    }
  }

  function chooseStation(slot: number) {
    goto(`/stations?slot=${slot}`);
  }
</script>

{#if !hideInAP || $currentMode !== 'ap'}
  <div class="grid gap-4 md:grid-cols-3">
    {#if error}
      <Card>
        <p class="text-red-500">{error}</p>
      </Card>
    {:else}
      {#each stations as station, i (station.slot || i)}
        <Card>
          <div class="flex flex-col gap-4">
            <div class="flex justify-between items-center">
              <h5 class="text-gray-700">{station.slot.toString().padStart(2, '0')}</h5>
            </div>
            <p class="text-xl font-bold">{station.name || 'No station assigned'}</p>
            <div class="flex flex-col gap-2">
              <Button
                color={currentPlayingSlot === station.slot ? "red" : "primary"}
                class="w-full"
                on:click={() => toggleStation(station.slot)}
              >
                {currentPlayingSlot === station.slot ? 'Stop' : 'Play'}
              </Button>
              <Button
                color="alternative"
                class="w-full"
                on:click={() => chooseStation(station.slot)}
              >
                Choose Station
              </Button>
            </div>
          </div>
        </Card>
      {/each}
    {/if}
  </div>
{/if} 