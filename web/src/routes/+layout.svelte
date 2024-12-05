<script lang="ts">
  import "../app.css";
  import { Navbar } from 'flowbite-svelte';
  import { DarkMode } from 'flowbite-svelte';
</script>

<svelte:head>
  <title>Internet Radio</title>
</svelte:head>

<Navbar fluid={true} class="fixed w-full z-20 top-0 start-0 border-b">
  <span class="self-center text-xl font-semibold whitespace-nowrap">Internet Radio</span>
  <div class="flex items-center">
    <DarkMode />
  </div>
</Navbar>

<main class="container mx-auto p-4 mt-16">
  <slot />
</main>
