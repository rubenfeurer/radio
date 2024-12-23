<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { Card, Button, Badge, Table, TableBody, TableBodyRow, TableBodyCell, TableHead, TableHeadCell, Alert } from 'flowbite-svelte';
  import { ws as wsStore } from '$lib/stores/websocket';
  import { currentMode } from '$lib/stores/mode';
  import { API_V1_STR, WS_URL } from '$lib/config';

  // State for system info and processes
  let systemInfo = {
    hostname: 'Loading...',
    ip: 'Loading...',
    cpuUsage: 'Loading...',
    diskSpace: 'Loading...',
    temperature: 'Loading...',
    hotspot_ssid: 'Loading...',
    internet_connected: false
  };

  let services = [];
  let wsConnected = false;
  let monitorWs: WebSocket | null = null;
  let isFirstConnection = true;
  let reconnectTimer: NodeJS.Timeout | null = null;

  // Initialize with API call
  async function fetchInitialData() {
    try {
      const response = await fetch(`${API_V1_STR}/monitor/status`);
      if (!response.ok) throw new Error('Failed to fetch monitor data');
      const data = await response.json();
      updateMonitorData(data);
    } catch (e) {
      console.error('Error fetching initial data:', e);
    }
  }

  // Setup WebSocket connection for live updates
  function setupWebSocket() {
    if (monitorWs) monitorWs.close();
    
    const wsBase = WS_URL.substring(0, WS_URL.indexOf('/api/v1'));
    const wsUrl = `${wsBase}${API_V1_STR}/monitor/ws`;
    
    console.log('Monitor: Connecting to WebSocket:', wsUrl);
    monitorWs = new WebSocket(wsUrl);
    
    monitorWs.onopen = async () => {
        console.log('Monitor: WebSocket connected');
        wsConnected = true;
        
        // Fetch fresh data when connection is established
        try {
            const response = await fetch(`${API_V1_STR}/monitor/status`);
            if (!response.ok) throw new Error('Failed to fetch monitor data');
            const data = await response.json();
            updateMonitorData(data);
        } catch (e) {
            console.error('Monitor: Error fetching initial data:', e);
        }
    };

    monitorWs.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            // Only log non-monitor updates to reduce console spam
            if (data.type !== 'monitor_update') {
                console.log('Monitor: Message received:', data.type);
            }
            if (data.type === 'monitor_update') {
                updateMonitorData(data.data);
            }
        } catch (e) {
            console.error('Monitor: Error handling message:', e);
        }
    };

    monitorWs.onerror = (error) => {
        wsConnected = false;
    };

    monitorWs.onclose = () => {
        console.log('Monitor: WebSocket closed, scheduling reconnect...');
        wsConnected = false;
        
        // Always attempt to reconnect
        if (reconnectTimer) clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(() => {
            console.log('Monitor: Attempting reconnection...');
            setupWebSocket();
        }, 3000);
    };
  }

  function updateMonitorData(data: any) {
    // Reduce console logging
    if (data.systemInfo) {
        systemInfo = { ...data.systemInfo };
        
        if (data.systemInfo.mode) {
            const newMode = data.systemInfo.mode.toLowerCase();
            if (newMode !== $currentMode) {
                console.log('Mode changed:', newMode);
                currentMode.set(newMode);
            }
        }
    }
    if (data.services) {
        services = [...data.services];
    }
  }

  onMount(async () => {
    await fetchInitialData();
    setupWebSocket();
    
    return () => {
        clearTimeout(reconnectTimer);
        if (monitorWs) monitorWs.close();
    };
  });

  onDestroy(() => {
    clearTimeout(reconnectTimer);
    if (monitorWs) monitorWs.close();
  });

  // Watch for mode changes and force reconnect
  $: if ($currentMode) {
    console.log('Monitor: Mode changed to:', $currentMode);
    setupWebSocket();
  }

  // Add explicit props for Flowbite components
  let tableHeadClass = '';
  let tableCellClass = '';
  let tableBodyClass = '';
  let cardClass = '';
  let badgeClass = '';
</script>

<div class="max-w-4xl mx-auto p-4">
  <!-- Temperature Warning Alert -->
  {#if parseFloat(systemInfo.temperature) > 70}
    <Alert color="red" class="mb-6">
      <span class="font-medium">Warning!</span>
      System temperature is {systemInfo.temperature} - This is above safe operating levels. Please check system cooling.
    </Alert>
  {/if}

  <!-- System Info Cards -->
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
    <!-- Network Mode Card -->
    <Card>
      <h3 class="text-sm font-medium text-gray-500">Network Mode</h3>
      <div class="mt-1 flex items-center gap-2">
        {#if !$currentMode}
          <p class="text-lg flex items-center gap-2">
            <span>Loading mode... (current value: {$currentMode})</span>
            <Badge color="gray">Waiting</Badge>
          </p>
        {:else if $currentMode.toLowerCase() === 'ap' || $currentMode.toLowerCase() === 'client'}
          <p class="text-lg">
            {$currentMode.toLowerCase() === 'ap' ? 'Access Point' : 'Client'}
          </p>
          <Badge color={$currentMode.toLowerCase() === 'ap' ? 'red' : 'blue'}>
            {$currentMode.toLowerCase() === 'ap' ? 'AP' : 'Client'}
          </Badge>
        {:else}
          <p class="text-lg flex items-center gap-2">
            <span>Unknown Mode: {$currentMode}</span>
            <Badge color="red">Error</Badge>
          </p>
          <p class="text-sm text-gray-500">
            Expected 'ap' or 'client', got '{$currentMode}'
          </p>
        {/if}
      </div>
    </Card>

    <!-- Hotspot Status Card - Always shown -->
    <Card>
      <h3 class="text-sm font-medium text-gray-500">Hotspot Status</h3>
      <div class="mt-1">
        {#if systemInfo.hotspot_ssid}
          <p class="text-lg flex items-center gap-2">
            <span>SSID: {systemInfo.hotspot_ssid}</span>
            <Badge color="green">Active</Badge>
          </p>
          <p class="text-sm text-gray-500 mt-1">IP: {systemInfo.ip}</p>
        {:else}
          <p class="text-lg">Hotspot turned off</p>
        {/if}
      </div>
    </Card>

    <!-- Hostname Card -->
    <Card>
      <h3 class="text-sm font-medium text-gray-500">Hostname</h3>
      <p class="mt-1 text-lg">{systemInfo.hostname}</p>
    </Card>

    <!-- IP Address Card -->
    <Card>
      <h3 class="text-sm font-medium text-gray-500">IP Address</h3>
      <p class="mt-1 text-lg">{systemInfo.ip}</p>
    </Card>

    <!-- CPU Usage Card -->
    <Card>
      <h3 class="text-sm font-medium text-gray-500">CPU Usage</h3>
      <p class="mt-1 text-lg">{systemInfo.cpuUsage}</p>
    </Card>

    <!-- Disk Space Card -->
    <Card>
      <h3 class="text-sm font-medium text-gray-500">Disk Space</h3>
      <p class="mt-1 text-lg">{systemInfo.diskSpace}</p>
    </Card>

    <!-- Temperature Card -->
    <Card>
      <h3 class="text-sm font-medium text-gray-500">Temperature</h3>
      <p class="mt-1 text-lg">
        <span class={
          parseFloat(systemInfo.temperature) > 80 ? 'text-red-600' :
          parseFloat(systemInfo.temperature) > 70 ? 'text-orange-500' :
          parseFloat(systemInfo.temperature) > 60 ? 'text-yellow-500' :
          'text-green-600'
        }>
          {systemInfo.temperature}
        </span>
      </p>
    </Card>

    <!-- WebSocket Status Card - Add this to the grid of system info cards -->
    <Card>
      <h3 class="text-sm font-medium text-gray-500">WebSocket Status</h3>
      <div class="mt-1 flex items-center gap-2">
        <p class="text-lg">
          {wsConnected ? 'Connected' : 'Disconnected'}
        </p>
        <Badge color={wsConnected ? "green" : "red"}>
          {wsConnected ? "Online" : "Offline"}
        </Badge>
      </div>
      {#if !wsConnected}
        <p class="text-sm text-red-500 mt-1">
          Attempting to reconnect...
        </p>
      {/if}
    </Card>

    <!-- Internet Connection Card -->
    <Card>
      <h3 class="text-sm font-medium text-gray-500">Internet Connection</h3>
      <div class="mt-1 flex items-center gap-2">
        <p class="text-lg">
          {systemInfo.internet_connected ? 'Connected' : 'No Connection'}
        </p>
        <Badge color={systemInfo.internet_connected ? "green" : "red"}>
          {systemInfo.internet_connected ? "Online" : "Offline"}
        </Badge>
      </div>
      {#if !systemInfo.internet_connected && $currentMode === 'client'}
        <p class="text-sm text-red-500 mt-1">
          Connected to WiFi but no internet access
        </p>
      {/if}
    </Card>
  </div>

  <!-- Processes Table -->
  <Card class="w-full">
    <Table class="w-full">
      <TableHead>
        <TableHeadCell>Process</TableHeadCell>
        <TableHeadCell>Status</TableHeadCell>
      </TableHead>
      
      <TableBody>
        {#each services as service}
          <TableBodyRow>
            <TableBodyCell>{service.name}</TableBodyCell>
            <TableBodyCell>
              <Badge
                color={service.status === 'active' || service.status === 'running' ? 'green' : 'red'}
              >
                {service.status}
              </Badge>
            </TableBodyCell>
          </TableBodyRow>
        {/each}
      </TableBody>
    </Table>
  </Card>
</div>

<style>
  :global(body) {
    background-color: rgb(249, 250, 251);
  }
</style> 