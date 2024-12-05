<script lang="ts">
  import { onMount } from 'svelte';
  import { Card, Button, Range, Badge } from 'flowbite-svelte';

  // Types
  interface RadioStation {
    name: string;
    url: string;
    slot: number;
    isPlaying: boolean;
  }

  // Mock data for now - will be replaced with WebSocket data
  let stations: RadioStation[] = [
    { name: "Station 1", url: "", slot: 1, isPlaying: false },
    { name: "Station 2", url: "", slot: 2, isPlaying: false },
    { name: "Station 3", url: "", slot: 3, isPlaying: false }
  ];
  let volume = 50;
  let wsConnected = false;

  // WebSocket setup
  let ws: WebSocket;
  
  onMount(() => {
    connectWebSocket();
    return () => ws?.close();
  });

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
    stations = stations.map(station => ({
      ...station,
      isPlaying: station.slot === data.current_station
    }));
  }

  function toggleStation(slot: number) {
    ws?.send(JSON.stringify({
      type: 'station_control',
      data: { slot, action: 'toggle' }
    }));
  }

  function updateVolume(event: CustomEvent) {
    const newVolume = event.detail;
    ws?.send(JSON.stringify({
      type: 'volume_control',
      data: { volume: newVolume }
    }));
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
            <Badge color={station.isPlaying ? "green" : "gray"}>
              {station.isPlaying ? "Playing" : "Stopped"}
            </Badge>
          </div>
          <p class="text-gray-700">{station.name || 'No station assigned'}</p>
          <Button
            color={station.isPlaying ? "red" : "primary"}
            class="w-full"
            on:click={() => toggleStation(station.slot)}
          >
            {station.isPlaying ? 'Stop' : 'Play'}
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
