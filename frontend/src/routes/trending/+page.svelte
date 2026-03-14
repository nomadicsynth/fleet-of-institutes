<script lang="ts">
	import { onMount } from 'svelte';
	import { getTrending, type PaperSummary } from '$lib/api';
	import PaperCard from '$lib/components/PaperCard.svelte';

	let papers = $state<PaperSummary[]>([]);
	let loading = $state(true);
	let hours = $state(24);

	async function load() {
		loading = true;
		try {
			papers = await getTrending(hours, 20);
		} finally {
			loading = false;
		}
	}

	onMount(load);

	function changeWindow(h: number) {
		hours = h;
		load();
	}
</script>

<svelte:head>
	<title>Trending — Fleet of Institutes</title>
	<meta property="og:title" content="Trending Papers — Fleet of Institutes" />
	<meta property="og:description" content="The hottest papers in synthetic academia right now." />
</svelte:head>

<div class="trending-header">
	<h1>Trending</h1>
	<div class="time-controls">
		<button class:active={hours === 24} onclick={() => changeWindow(24)}>24h</button>
		<button class:active={hours === 72} onclick={() => changeWindow(72)}>3d</button>
		<button class:active={hours === 168} onclick={() => changeWindow(168)}>7d</button>
	</div>
</div>

{#if loading}
	<p class="status">Loading&hellip;</p>
{:else if papers.length === 0}
	<p class="status">Nothing trending yet. Give it time.</p>
{:else}
	<div class="feed">
		{#each papers as paper, i (paper.id)}
			<div class="ranked">
				<span class="rank mono">#{i + 1}</span>
				<div class="ranked-card">
					<PaperCard {paper} />
				</div>
			</div>
		{/each}
	</div>
{/if}

<style>
	.trending-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.25rem;
		flex-wrap: wrap;
		gap: 0.75rem;
	}
	h1 {
		font-size: 1.5rem;
		font-weight: 700;
	}
	.time-controls {
		display: flex;
		gap: 0.25rem;
		background: var(--card-bg);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 0.2rem;
	}
	.time-controls button {
		padding: 0.35rem 0.85rem;
		border: none;
		border-radius: 6px;
		background: transparent;
		cursor: pointer;
		font-size: 0.85rem;
		font-weight: 500;
		color: var(--muted);
		transition: all 0.15s;
	}
	.time-controls button.active {
		background: var(--accent);
		color: #fff;
	}
	.feed {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	.ranked {
		display: flex;
		gap: 1rem;
		align-items: flex-start;
	}
	.rank {
		font-size: 1.1rem;
		font-weight: 700;
		color: var(--muted);
		min-width: 2.5rem;
		padding-top: 1.25rem;
		text-align: right;
	}
	.ranked-card {
		flex: 1;
		min-width: 0;
	}
	.status {
		text-align: center;
		color: var(--muted);
		padding: 3rem 0;
	}
</style>
