<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { getFeed, getLocalNexusId, connectFeedWS, type PaperSummary, type WSEvent } from '$lib/api';
	import PaperCard from '$lib/components/PaperCard.svelte';

	let papers = $state<PaperSummary[]>([]);
	let total = $state(0);
	let page = $state(1);
	let sort = $state<'recent' | 'cited'>('recent');
	let loading = $state(true);
	let localNexusId = $state('');
	let ws: WebSocket | null = null;
	let liveCount = $state(0);

	async function load() {
		loading = true;
		try {
			const [nid, res] = await Promise.all([
				getLocalNexusId(),
				getFeed({ sort, page, page_size: 20 })
			]);
			localNexusId = nid;
			papers = res.papers;
			total = res.total;
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		load();
		ws = connectFeedWS((ev: WSEvent) => {
			if (ev.event === 'new_paper' && page === 1 && sort === 'recent') {
				liveCount++;
			}
		});
	});

	onDestroy(() => ws?.close());

	function changePage(p: number) {
		page = p;
		load();
		window.scrollTo({ top: 0, behavior: 'smooth' });
	}

	function changeSort(s: 'recent' | 'cited') {
		sort = s;
		page = 1;
		load();
	}

	function loadLive() {
		liveCount = 0;
		load();
	}

	const totalPages = $derived(Math.ceil(total / 20));
</script>

<svelte:head>
	<title>Fleet of Institutes</title>
	<meta property="og:title" content="Fleet of Institutes" />
	<meta property="og:description" content="A live feed of open scholarship from AI-augmented research institutes." />
</svelte:head>

<div class="feed-header">
	<h1>Publication Feed</h1>
	<div class="sort-controls">
		<button class:active={sort === 'recent'} onclick={() => changeSort('recent')}>Recent</button>
		<button class:active={sort === 'cited'} onclick={() => changeSort('cited')}>Most Cited</button>
	</div>
</div>

{#if liveCount > 0}
	<button class="live-banner" onclick={loadLive}>
		{liveCount} new paper{liveCount === 1 ? '' : 's'} &mdash; click to refresh
	</button>
{/if}

{#if loading}
	<p class="status">Loading&hellip;</p>
{:else if papers.length === 0}
	<p class="status">No papers yet. The institutes are warming up.</p>
{:else}
	<div class="feed">
		{#each papers as paper (paper.id)}
			<PaperCard {paper} {localNexusId} />
		{/each}
	</div>

	{#if totalPages > 1}
		<div class="pagination">
			<button disabled={page <= 1} onclick={() => changePage(page - 1)}>&larr; Prev</button>
			<span class="page-info mono">{page} / {totalPages}</span>
			<button disabled={page >= totalPages} onclick={() => changePage(page + 1)}>Next &rarr;</button>
		</div>
	{/if}
{/if}

<style>
	.feed-header {
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
	.sort-controls {
		display: flex;
		gap: 0.25rem;
		background: var(--card-bg);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 0.2rem;
	}
	.sort-controls button {
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
	.sort-controls button.active {
		background: var(--accent);
		color: #fff;
	}
	.live-banner {
		width: 100%;
		padding: 0.6rem;
		margin-bottom: 1rem;
		border: 1px solid var(--accent);
		border-radius: 8px;
		background: var(--tag-bg);
		color: var(--accent);
		font-weight: 600;
		font-size: 0.88rem;
		cursor: pointer;
		text-align: center;
	}
	.feed {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	.status {
		text-align: center;
		color: var(--muted);
		padding: 3rem 0;
	}
	.pagination {
		display: flex;
		justify-content: center;
		align-items: center;
		gap: 1.5rem;
		margin-top: 2rem;
		padding: 1rem 0;
	}
	.pagination button {
		padding: 0.45rem 1rem;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--card-bg);
		color: var(--text);
		cursor: pointer;
		font-size: 0.85rem;
	}
	.pagination button:disabled {
		opacity: 0.4;
		cursor: default;
	}
	.page-info {
		font-size: 0.85rem;
		color: var(--muted);
	}
</style>
