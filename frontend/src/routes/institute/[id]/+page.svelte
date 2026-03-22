<script lang="ts">
	import type { PageProps } from './$types';
	import { onMount } from 'svelte';
	import {
		getInstitute,
		getFeed,
		getLocalNexusId,
		formatInstituteAttribution,
		type Institute,
		type PaperSummary
	} from '$lib/api';
	import Avatar from '$lib/components/Avatar.svelte';
	import PaperCard from '$lib/components/PaperCard.svelte';

	let { params }: PageProps = $props();
	let institute = $state<Institute | null>(null);
	let papers = $state<PaperSummary[]>([]);
	let localNexusId = $state('');
	let error = $state('');

	onMount(async () => {
		const id = params.id;
		try {
			const [nid, inst, feed] = await Promise.all([
				getLocalNexusId(),
				getInstitute(id),
				getFeed({ institute: id, page_size: 50 })
			]);
			localNexusId = nid;
			institute = inst;
			papers = feed.papers;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load institute';
		}
	});

	const profileAttribution = $derived(
		institute
			? formatInstituteAttribution(institute.name, institute.origin_nexus, localNexusId)
			: { primary: '', suffix: null as string | null, title: null as string | null }
	);

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleDateString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric'
		});
	}

	const tags = $derived(institute?.tags ? institute.tags.split(',').map((t) => t.trim()) : []);
</script>

<svelte:head>
	{#if institute}
		<title>{institute.name} — Fleet of Institutes</title>
		<meta property="og:title" content={institute.name} />
		<meta property="og:description" content={institute.mission} />
	{:else}
		<title>Institute — Fleet of Institutes</title>
	{/if}
</svelte:head>

{#if error}
	<p class="error">{error}</p>
{:else if !institute}
	<p class="status">Loading&hellip;</p>
{:else}
	<div class="profile">
		<div class="profile-header">
			<Avatar seed={institute.avatar_seed} size={64} />
			<div>
				<h1 title={profileAttribution.title ?? undefined}>
					{profileAttribution.primary}{#if profileAttribution.suffix}<span class="origin-suffix"
							>{profileAttribution.suffix}</span
						>{/if}
				</h1>
				{#if institute.mission}
					<p class="mission">{institute.mission}</p>
				{/if}
			</div>
		</div>

		<div class="stats-row">
			<div class="stat">
				<span class="stat-num">{institute.paper_count}</span>
				<span class="stat-label">Papers</span>
			</div>
			<div class="stat">
				<span class="stat-num">{institute.citation_count}</span>
				<span class="stat-label">Citations</span>
			</div>
			<div class="stat">
				<span class="stat-num mono">{formatDate(institute.registered_at)}</span>
				<span class="stat-label">Founded</span>
			</div>
		</div>

		{#if tags.length > 0}
			<div class="tags">
				{#each tags as tag (tag)}
					<span class="tag">{tag}</span>
				{/each}
			</div>
		{/if}
	</div>

	{#if papers.length > 0}
		<h2 class="section-title">Publications</h2>
		<div class="feed">
			{#each papers as paper (paper.id)}
				<PaperCard {paper} {localNexusId} />
			{/each}
		</div>
	{:else}
		<p class="status">No publications yet.</p>
	{/if}
{/if}

<style>
	.profile {
		background: var(--card-bg);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.5rem;
		margin-bottom: 2rem;
	}
	.profile-header {
		display: flex;
		gap: 1rem;
		align-items: flex-start;
		margin-bottom: 1.25rem;
	}
	h1 {
		font-size: 1.5rem;
		line-height: 1.3;
		margin-bottom: 0.25rem;
	}
	.origin-suffix {
		font-weight: 600;
		color: var(--muted);
		margin-left: 0.2em;
	}
	.mission {
		color: var(--text-secondary);
		font-style: italic;
		font-size: 0.95rem;
	}
	.stats-row {
		display: flex;
		gap: 2rem;
		margin-bottom: 1rem;
		flex-wrap: wrap;
	}
	.stat {
		display: flex;
		flex-direction: column;
	}
	.stat-num {
		font-size: 1.25rem;
		font-weight: 700;
	}
	.stat-label {
		font-size: 0.78rem;
		color: var(--muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.tags {
		display: flex;
		gap: 0.35rem;
		flex-wrap: wrap;
	}
	.tag {
		font-size: 0.72rem;
		padding: 0.15rem 0.5rem;
		border-radius: 99px;
		background: var(--tag-bg);
		color: var(--tag-text);
		font-family: 'IBM Plex Mono', monospace;
	}
	.section-title {
		font-size: 1.1rem;
		font-weight: 600;
		margin-bottom: 1rem;
	}
	.feed {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	.error, .status {
		text-align: center;
		color: var(--muted);
		padding: 3rem 0;
	}
	.error {
		color: #b33030;
	}
</style>
