<script lang="ts">
  import { onMount } from 'svelte';
  import { Card, Button, Range, Badge } from 'flowbite-svelte';

  // Types
  interface RadioStation {
    name: string;
    url: string;
    slot: number;
  }

  let stations: RadioStation[] = [];
  let volume = 50;
  let wsConnected = false;
  let currentPlayingSlot: number | null = null;

  // WebSocket setup
  let ws: WebSocket;
  
  onMount(() => {
    loadInitialStations();
    fetchVolume();
    connectWebSocket();
    return () => ws?.close();
  });

  async function loadInitialStations() {
    try {
      // Load stations for slots 1, 2, and 3
      const slots = [1, 2, 3];
      for (const slot of slots) {
        try {
          const response = await fetch(`http://radiod.local:8000/api/v1/stations/${slot}`);
          if (response.ok) {
            const station = await response.json();
            stations = [...stations, station];
          }
        } catch (error) {
          console.error(`Failed to fetch station ${slot}:`, error);
        }
      }
    } catch (error) {
      console.error("Failed to fetch stations:", error);
    }
  }

  async function fetchVolume() {
    try {
      const response = await fetch('http://radiod.local:8000/api/v1/volume');
      const data = await response.json();
      volume = data.volume;
    } catch (error) {
      console.error("Failed to fetch volume:", error);
    }
  }

  function connectWebSocket() {
    ws = new WebSocket(`ws://radiod.local:8000/ws`);
    
    ws.onopen = () => {
      wsConnected = true;
      // Request initial status
      ws?.send(JSON.stringify({ type: "status_request" }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'status_response' || data.type === 'status_update') {
        updateStatus(data.data);
      }
    };

    ws.onclose = () => {
      wsConnected = false;
      // Reconnect after 1 second
      setTimeout(connectWebSocket, 1000);
    };
  }

  function updateStatus(data: any) {
    volume = data.volume;
    currentPlayingSlot = data.current_station;
  }

  async function toggleStation(slot: number) {
    try {
      const response = await fetch(`http://radiod.local:8000/api/v1/stations/${slot}/toggle`, {
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

  async function updateVolume(event: CustomEvent) {
    const newVolume = event.detail;
    try {
      await fetch('http://radiod.local:8000/api/v1/volume', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ volume: newVolume })
      });
      volume = newVolume;
    } catch (error) {
      console.error("Failed to update volume:", error);
    }
  }
</script>

<div class="max-w-4xl mx-auto p-4">
  <!-- Connection Status -->
  <div class="mb-6 flex justify-between items-center">
    <h1 class="text-2xl font-bold">Internet Radio</h1>
    <Badge color={wsConnected ? "green" : "red"}>
      {wsConnected ? "Connected" : "Disconnected"}
    </Badge>
  </div>

  <!-- Radio Stations -->
  <div class="grid gap-4 md:grid-cols-3 mb-8">
    {#each stations as station (station.slot)}
      <Card padding="xl">
        <div class="flex flex-col gap-4">
          <div class="flex justify-between items-center">
            <h5 class="text-xl font-bold">Slot {station.slot}</h5>
            <Badge color={currentPlayingSlot === station.slot ? "green" : "gray"}>
              {currentPlayingSlot === station.slot ? "Playing" : "Stopped"}
            </Badge>
          </div>
          <p class="text-gray-700">{station.name || 'No station assigned'}</p>
          <Button
            color={currentPlayingSlot === station.slot ? "red" : "primary"}
            class="w-full"
            on:click={() => toggleStation(station.slot)}
          >
            {currentPlayingSlot === station.slot ? 'Stop' : 'Play'}
          </Button>
        </div>
      </Card>
    {/each}
  </div>

  <!-- Volume Control -->
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
</div>