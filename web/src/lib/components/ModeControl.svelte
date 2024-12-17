<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { websocketStore } from '$lib/stores/websocket';
    import { currentMode } from '$lib/stores/mode';
    import { Card, Badge, Button } from 'flowbite-svelte';
    import { browser } from '$app/environment';

    let isLoading = false;
    let error: string | null = null;

    const currentHost = browser ? window.location.hostname : '';
    const API_BASE = browser 
        ? (window.location.port === '5173' 
            ? `http://${currentHost}:80`
            : '')
        : '';

    // Subscribe to WebSocket updates
    const unsubscribe = websocketStore.subscribe(($ws) => {
        if ($ws?.data?.type === 'mode_update') {
            $currentMode = $ws.data.mode;
            isLoading = false;
        }
    });

    async function getCurrentMode() {
        try {
            const response = await fetch(`${API_BASE}/api/v1/mode/current`);
            if (!response.ok) {
                throw new Error('Failed to fetch mode');
            }
            const data = await response.json();
            $currentMode = data.mode;
        } catch (err) {
            error = 'Failed to get current mode';
            console.error('Error fetching mode:', err);
        }
    }

    async function toggleMode() {
        try {
            isLoading = true;
            error = null;
            const response = await fetch(`${API_BASE}/api/v1/mode/toggle`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Failed to toggle mode');
            }
            
            // Mode update will come through WebSocket
        } catch (err) {
            error = err.message || 'Failed to toggle mode';
            isLoading = false;
            console.error('Error toggling mode:', err);
        }
    }

    onMount(() => {
        getCurrentMode();
    });

    onDestroy(() => {
        unsubscribe();
    });

    // Simple SVG icons
    const ModeIcons = {
        ap: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z" />
        </svg>`,
        client: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
        </svg>`
    };
</script>

<Card>
    <div class="flex flex-col gap-2">
        <span class="text-sm text-gray-500">Network Mode</span>
        <div class="flex items-center gap-2">
            <h3 class="text-lg font-semibold">
                {currentMode === 'ap' ? 'Access Point' : 'Client'}
            </h3>
            <Badge color={currentMode === 'ap' ? 'red' : 'blue'}>
                {@html currentMode === 'ap' ? ModeIcons.ap : ModeIcons.client}
                {currentMode === 'ap' ? 'AP' : 'Client'}
            </Badge>
        </div>

        {#if error}
            <Badge color="red" class="my-1">{error}</Badge>
        {/if}

        <Button 
            color="alternative" 
            class="w-full mt-2"
            disabled={isLoading}
            on:click={toggleMode}
        >
            {#if isLoading}
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-500" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
            {/if}
            Switch to {currentMode === 'ap' ? 'Client' : 'AP'} Mode
        </Button>
    </div>
</Card> 