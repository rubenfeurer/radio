<script lang="ts">
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { Card, Button, Badge, Table, TableBody, TableBodyRow, TableBodyCell, TableHead, TableHeadCell, Alert } from 'flowbite-svelte';

  // State for system info and processes
  let systemInfo = {
    hostname: 'Loading...',
    ip: 'Loading...',
    cpuUsage: 'Loading...',
    diskSpace: 'Loading...',
    temperature: 'Loading...'
  };

  let services = [];
  let ws: WebSocket;
  let wsConnected = false;

  // Get the current hostname (IP or domain)
  const currentHost = browser ? window.location.hostname : '';
  
  function connectWebSocket() {
    if (!browser) return;
    
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = currentHost;
    const wsPort = window.location.port === '5173' ? '80' : window.location.port;
    
    // Use the main WebSocket endpoint
    const wsUrl = `${wsProtocol}//${wsHost}${wsPort ? ':' + wsPort : ''}/api/v1/ws`;
    console.log('Connecting to WebSocket:', wsUrl);
    
    try {
      ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        wsConnected = true;
        // Request initial monitor data
        ws.send(JSON.stringify({ type: "monitor_request" }));
      };

      ws.onmessage = (event) => {
        console.log('Raw WebSocket message received:', event.data);
        try {
          const data = JSON.parse(event.data);
          console.log('Parsed monitor data:', data);
          
          switch(data.type) {
            case 'monitor_update':
              console.log('Received monitor update:', data.data);
              if (data.data.systemInfo) {
                systemInfo = data.data.systemInfo;
              }
              if (data.data.services) {
                services = data.data.services;
              }
              break;
            
            case 'status_response':
              console.log('Received initial status, requesting monitor data');
              ws.send(JSON.stringify({ 
                type: "monitor_request",
                data: { requestType: "full" }  // Add more context to request
              }));
              break;
            
            default:
              console.log('Unknown message type:', data.type);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket closed');
        wsConnected = false;
        // Reconnect after 1 second
        setTimeout(connectWebSocket, 1000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        wsConnected = false;
      };

      return ws;
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      wsConnected = false;
    }
  }

  onMount(() => {
    if (browser) {
      console.log('Component mounted, initializing WebSocket');
      const ws = connectWebSocket();
      
      // Set up periodic monitor requests
      const interval = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          console.log('Sending periodic monitor request');
          ws.send(JSON.stringify({ 
            type: "monitor_request",
            data: { requestType: "update" }
          }));
        }
      }, 5000);

      return () => {
        clearInterval(interval);
        if (ws) {
          ws.close();
          wsConnected = false;
        }
      };
    }
  });

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

  <!-- Header with Back Button and Connection Status -->
  <div class="mb-6 flex justify-between items-center">
    <div class="flex items-center gap-4">
      <a href="/" class="text-gray-500 hover:text-gray-700">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
      </a>
      <h1 class="text-2xl font-bold">System Monitor</h1>
    </div>
    <div class="text-sm">
      Status: <span class={wsConnected ? 'text-green-600' : 'text-red-600'}>{wsConnected ? 'Connected' : 'Disconnected'}</span>
    </div>
  </div>

  <!-- System Info Cards -->
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
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