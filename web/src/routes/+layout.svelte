<script lang="ts">
  import "../app.css";
  import { Navbar } from 'flowbite-svelte';
  import { goto } from '$app/navigation';
</script>

<svelte:head>
  <title>Radio</title>
</svelte:head>

<Navbar fluid={true} class="fixed w-full z-20 top-0 start-0 border-b">
  <span 
    class="self-center text-xl font-semibold whitespace-nowrap cursor-pointer"
    on:click={() => goto('/')}
  >
    Radio
  </span>
</Navbar>

<main class="container mx-auto p-4 mt-16 bg-white">
  <slot />
</main>
