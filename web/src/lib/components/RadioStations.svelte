<script lang="ts">
  import { Card, Button, Badge } from 'flowbite-svelte';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { onMount } from 'svelte';
  import { ws } from '$lib/stores/websocket';  // Import the WebSocket store

  // Types
  interface RadioStation {
    name: string;
    url: string;
    slot: number;
    country?: string | null;
    location?: string | null;
  }

  // Move state here
  let stations: RadioStation[] = [];
  let currentPlayingSlot: number | null = null;

  // Get the current hostname (IP or domain)
  const currentHost = browser ? window.location.hostname : '';
  
  // Determine API base URL
  const API_BASE = browser 
    ? (window.location.port === '5173' 
      ? `http://${currentHost}:80`
      : '')
    : '';

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

            // Handle current_station whether it's a number or an object
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

  onMount(() => {
    console.log('Component mounted, requesting initial status');
    ws.sendMessage({ type: "status_request" });
    loadInitialStations();
  });

  export async function loadInitialStations() {
    try {
        console.log("Fetching assigned stations...");
        const assignedResponse = await fetch(`${API_BASE}/api/v1/stations/assigned`);
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
                    // Use assigned station from file
                    stations = [...stations, {
                        ...assignedStations[slot],
                        slot: parseInt(slot)
                    }];
                } else {
                    // Create empty slot
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
      const response = await fetch(`${API_BASE}/api/v1/stations/${slot}/toggle`, {
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

<div class="grid gap-4 md:grid-cols-3 mb-8">
  {#each stations as station, i (station.slot || i)}
    <Card padding="xl">
      <div class="flex flex-col gap-4">
        <div class="flex justify-between items-center">
          <h5 class="text-xl font-bold">Slot {station.slot}</h5>
          <Badge color={currentPlayingSlot === station.slot ? "green" : "gray"}>
            {currentPlayingSlot === station.slot ? "Playing" : "Stopped"}
          </Badge>
        </div>
        <p class="text-gray-700">{station.name || 'No station assigned'}</p>
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
</div> 