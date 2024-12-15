<!-- web/src/lib/components/ModeSwitch.svelte -->
<script lang="ts">
    import { Card, Button } from 'flowbite-svelte';
    
    export let API_BASE: string;
    export let currentMode: string;
    export let ws: WebSocket | null = null;
    
    async function switchMode() {
      try {
        const newMode = currentMode === 'AP' ? 'CLIENT' : 'AP';
        
        // First notify through WebSocket if in client mode
        if (currentMode === 'CLIENT' && ws) {
          ws.send(JSON.stringify({ 
            type: 'mode_change',
            data: { mode: 'AP' }
          }));
        }
        
        // Then make API call
        const response = await fetch(`${API_BASE}/api/v1/wifi/mode`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ mode: newMode })
        });
  
        if (!response.ok) {
          throw new Error('Failed to switch mode');
        }
  
        // If switching to AP mode, the device will restart and host its own network
        if (newMode === 'AP') {
          // Wait a moment then redirect to the AP address
          setTimeout(() => {
            window.location.href = 'http://192.168.4.1';
          }, 5000);
        }
        
      } catch (error) {
        console.error('Error switching mode:', error);
        alert('Failed to switch mode. Please try again.');
      }
    }
  </script>
  
  <Card class="mt-4">
    <div class="flex flex-col gap-2">
      <h3 class="text-lg font-semibold">Mode</h3>
      <div class="flex items-center justify-between">
        <span class="text-gray-600">Current: {currentMode} Mode</span>
        <Button
          color="purple"
          on:click={switchMode}
        >
          Change to {currentMode === 'AP' ? 'WiFi' : 'AP'} Mode
        </Button>
      </div>
    </div>
  </Card>