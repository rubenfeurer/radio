<script lang="ts">
  import { onMount } from 'svelte';
  import { Card, Button, Range, Badge } from 'flowbite-svelte';
  import { goto } from '$app/navigation';

  // Types
  interface RadioStation {
    name: string;
    url: string;
    slot: number;
    country?: string | null;
    location?: string | null;
  }

  interface WiFiStatus {
    ssid: string | null;
    signal_strength: number | null;
    is_connected: boolean;
    has_internet: boolean;
    available_networks: WiFiNetwork[];
  }

  interface WiFiNetwork {
    ssid: string;
    signal_strength: number;
    security: string | null;
    in_use: boolean;
  }

  let stations: RadioStation[] = [];
  let volume = 50;
  let wsConnected = false;
  let currentPlayingSlot: number | null = null;
  let wifiStatus: WiFiStatus = {
    ssid: null,
    signal_strength: null,
    is_connected: false,
    has_internet: false,
    available_networks: []
  };

  // WebSocket setup
  let ws: WebSocket;
  
  onMount(() => {
    loadInitialStations();
    fetchVolume();
    fetchWiFiStatus();
    connectWebSocket();
    return () => ws?.close();
  });

  async function loadInitialStations() {
    try {
        // First try to load assigned stations from file
        const assignedResponse = await fetch('/api/v1/stations/assigned');
        const assignedStations = await assignedResponse.json();
        
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
                    // Fall back to default station
                    const response = await fetch(`/api/v1/stations/${slot}`);
                    if (response.ok) {
                        const station = await response.json();
                        stations = [...stations, station];
                    }
                }
            } catch (error) {
                console.error(`Failed to fetch station ${slot}:`, error);
            }
        }
    } catch (error) {
        console.error("Failed to fetch stations:", error);
        // Only fall back to default stations if loading assigned stations completely fails
        const slots = [1, 2, 3];
        for (const slot of slots) {
            try {
                const response = await fetch(`/api/v1/stations/${slot}`);
                if (response.ok) {
                    const station = await response.json();
                    stations = [...stations, station];
                }
            } catch (error) {
                console.error(`Failed to fetch station ${slot}:`, error);
            }
        }
    }
  }

  async function fetchVolume() {
    try {
      const response = await fetch('/api/volume');
      const data = await response.json();
      volume = data.volume;
    } catch (error) {
      console.error("Failed to fetch volume:", error);
    }
  }

  async function fetchWiFiStatus() {
    try {
      const response = await fetch('/api/v1/wifi/status');
      if (!response.ok) {
        console.error('Failed to fetch WiFi status:', await response.text());
        return;
      }
      const data = await response.json();
      wifiStatus = data;
    } catch (error) {
      console.error("Failed to fetch WiFi status:", error);
    }
  }

  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
    
    ws.onopen = () => {
      wsConnected = true;
      // Request initial status
      ws?.send(JSON.stringify({ type: "status_request" }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'status_response' || data.type === 'status_update') {
        updateStatus(data.data);
      } else if (data.type === 'wifi_status') {
        wifiStatus = data.data;
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
      const response = await fetch(`/api/v1/stations/${slot}/toggle`, {
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
    // Convert to integer since Range might send float
    const newVolume = Math.round(Number(event.target.value));
    
    try {
      const response = await fetch('/api/v1/volume', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ volume: newVolume })
      });

      if (!response.ok) {
        const error = await response.json();
        console.error("Volume update failed:", error);
        return;
      }

      volume = newVolume;
    } catch (error) {
      console.error("Failed to update volume:", error);
    }
  }

  function chooseStation(slot: number) {
    goto(`/stations?slot=${slot}`);
  }

  // Simple SVG icons instead of flowbite-svelte-icons
  const WifiIcon = {
    on: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
    </svg>`,
    off: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>`
  };

  const LockIcon = `<svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
  </svg>`;
</script>

<div class="max-w-4xl mx-auto p-4">
  <!-- Connection Status -->
  <div class="mb-6 flex justify-between items-center">
    <h1 class="text-2xl font-bold">Radio</h1>
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

  <!-- WiFi Status Card -->
  <Card class="mb-4">
    <div class="flex flex-col gap-2">
      <span class="text-sm text-gray-500">WiFi</span>
      <div class="flex items-center gap-2">
        <h3 class="text-lg font-semibold">
          {wifiStatus.ssid || 'Not connected'}
        </h3>
        {#if wifiStatus.is_connected}
          {#if wifiStatus.has_internet}
            {@html WifiIcon.on}
          {/if}
          {#if wifiStatus.available_networks.find(n => n.ssid === wifiStatus.ssid)?.security}
            {@html LockIcon}
          {/if}
        {:else}
          <Badge color="red">
            {@html WifiIcon.off}
            Disconnected
          </Badge>
        {/if}
      </div>
      <a href="/wifi" class="w-full">
        <Button color="alternative" class="w-full mt-2">
          Settings
        </Button>
      </a>
    </div>
  </Card>
</div>