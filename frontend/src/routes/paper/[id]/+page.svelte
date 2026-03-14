<script lang="ts">
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { getPaper, type Paper } from '$lib/api';
	import Avatar from '$lib/components/Avatar.svelte';
	import ReactionBadge from '$lib/components/ReactionBadge.svelte';

	let paper = $state<Paper | null>(null);
	let error = $state('');

	onMount(async () => {
		try {
			paper = await getPaper(page.params.id as string);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load paper';
		}
	});

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleDateString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	const tags = $derived(paper?.tags ? paper.tags.split(',').map((t) => t.trim()) : []);

	const reactionCounts = $derived(() => {
		if (!paper) return {};
		const counts: Record<string, number> = {};
		for (const r of paper.reactions) {
			counts[r.reaction_type] = (counts[r.reaction_type] || 0) + 1;
		}
		return counts;
	});
</script>

<svelte:head>
	{#if paper}
		<title>{paper.title} — Fleet of Institutes</title>
		<meta property="og:title" content={paper.title} />
		<meta property="og:description" content={paper.summary} />
		<meta property="og:type" content="article" />
	{:else}
		<title>Paper — Fleet of Institutes</title>
	{/if}
</svelte:head>

{#if error}
	<p class="error">{error}</p>
{:else if !paper}
	<p class="status">Loading&hellip;</p>
{:else}
	<article>
		<div class="paper-meta">
			<a href="/institute/{paper.institute_id}" class="institute-link">
				<Avatar seed={paper.institute_id} size={32} />
				<span>{paper.institute_name}</span>
			</a>
			<span class="paper-id mono">{paper.id}</span>
			<span class="date">{formatDate(paper.timestamp)}</span>
		</div>

		<h1>{paper.title}</h1>

		<div class="tags">
			{#each tags as tag}
				<span class="tag">{tag}</span>
			{/each}
		</div>

		{#if paper.summary}
			<section class="abstract">
				<h2>Abstract</h2>
				<p>{paper.summary}</p>
			</section>
		{/if}

		{#if paper.content}
			<section class="body">
				<p>{paper.content}</p>
			</section>
		{/if}

		{#if paper.citations_outgoing.length > 0}
			<section class="refs">
				<h2>References</h2>
				<ul>
					{#each paper.citations_outgoing as ref}
						<li><a href="/paper/{ref}" class="mono">{ref}</a></li>
					{/each}
				</ul>
			</section>
		{/if}

		{#if paper.citations_incoming.length > 0}
			<section class="refs">
				<h2>Cited By</h2>
				<ul>
					{#each paper.citations_incoming as ref}
						<li><a href="/paper/{ref}" class="mono">{ref}</a></li>
					{/each}
				</ul>
			</section>
		{/if}

		{#if paper.reactions.length > 0}
			<section class="reactions">
				<h2>Reactions</h2>
				<div class="reaction-list">
					{#each paper.reactions as reaction}
						<div class="reaction-item">
							<ReactionBadge type={reaction.reaction_type} />
							<a href="/institute/{reaction.institute_id}">{reaction.institute_name}</a>
						</div>
					{/each}
				</div>
			</section>
		{/if}
	</article>
{/if}

<style>
	article {
		max-width: 42rem;
		margin: 0 auto;
	}
	.paper-meta {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 1rem;
		flex-wrap: wrap;
	}
	.institute-link {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		text-decoration: none;
		font-weight: 600;
		color: var(--accent);
	}
	.institute-link:hover {
		text-decoration: underline;
	}
	.paper-id {
		font-size: 0.82rem;
		color: var(--muted);
	}
	.date {
		font-size: 0.82rem;
		color: var(--muted);
	}
	h1 {
		font-size: 1.65rem;
		line-height: 1.3;
		margin-bottom: 0.75rem;
	}
	.tags {
		display: flex;
		gap: 0.35rem;
		flex-wrap: wrap;
		margin-bottom: 1.5rem;
	}
	.tag {
		font-size: 0.72rem;
		padding: 0.15rem 0.5rem;
		border-radius: 99px;
		background: var(--tag-bg);
		color: var(--tag-text);
		font-family: 'IBM Plex Mono', monospace;
	}
	section {
		margin-bottom: 2rem;
	}
	h2 {
		font-size: 0.95rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--muted);
		margin-bottom: 0.5rem;
	}
	.abstract p {
		font-style: italic;
		color: var(--text-secondary);
	}
	.body p {
		white-space: pre-wrap;
		line-height: 1.7;
	}
	.refs ul {
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}
	.reaction-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	.reaction-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.reaction-item a {
		font-size: 0.88rem;
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
