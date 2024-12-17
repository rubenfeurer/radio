<script lang="ts">
  import { onMount } from 'svelte';
  import { Card, Button, Badge, Table, TableBody, TableBodyRow, TableBodyCell, TableHead, TableHeadCell, Alert } from 'flowbite-svelte';
  import { ws as wsStore } from '$lib/stores/websocket';
  import { currentMode } from '$lib/stores/mode';  // Import mode store

  // State for system info and processes
  let systemInfo = {
    hostname: 'Loading...',
    ip: 'Loading...',
    cpuUsage: 'Loading...',
    diskSpace: 'Loading...',
    temperature: 'Loading...'
  };

  let services = [];
  let wsConnected = false;

  // Subscribe to WebSocket connection status
  wsStore.subscribe(socket => {
    wsConnected = socket !== null;
    
    if (socket) {
      // Listen for WebSocket messages
      socket.addEventListener('message', (event) => {
        try {
          const data = JSON.parse(event.data);
          
          switch(data.type) {
            case 'monitor_update':
              if (data.data.systemInfo) {
                systemInfo = data.data.systemInfo;
              }
              if (data.data.services) {
                services = data.data.services;
              }
              break;
            
            case 'status_response':
              wsStore.sendMessage({ 
                type: "monitor_request",
                data: { requestType: "full" }
              });
              break;
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      });
    }
  });

  onMount(() => {
    // Request initial monitor data
    wsStore.sendMessage({ 
      type: "monitor_request",
      data: { requestType: "full" }
    });

    // Set up periodic updates
    const interval = setInterval(() => {
      wsStore.sendMessage({ 
        type: "monitor_request",
        data: { requestType: "update" }
      });
    }, 5000);

    return () => {
      clearInterval(interval);
    };
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

  <!-- System Info Cards -->
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
    <!-- Network Mode Card -->
    <Card>
      <h3 class="text-sm font-medium text-gray-500">Network Mode</h3>
      <div class="mt-1 flex items-center gap-2">
        <p class="text-lg">{$currentMode === 'ap' ? 'Access Point' : 'Client'}</p>
        <Badge color={$currentMode === 'ap' ? 'red' : 'blue'}>
          {$currentMode === 'ap' ? 'AP' : 'Client'}
        </Badge>
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