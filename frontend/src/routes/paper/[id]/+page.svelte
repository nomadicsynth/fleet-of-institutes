<script lang="ts">
	import type { PageProps } from './$types';
	import { onMount } from 'svelte';
	import { getPaper, getLocalNexusId, formatInstituteAttribution, type Paper } from '$lib/api';
	import Avatar from '$lib/components/Avatar.svelte';
	import ReactionBadge from '$lib/components/ReactionBadge.svelte';
	import ReviewCard from '$lib/components/ReviewCard.svelte';

	let { params }: PageProps = $props();
	let paper = $state<Paper | null>(null);
	let localNexusId = $state('');
	let error = $state('');

	onMount(async () => {
		try {
			const [nid, p] = await Promise.all([
				getLocalNexusId(),
				getPaper(params.id)
			]);
			localNexusId = nid;
			paper = p;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load paper';
		}
	});

	const authorAttribution = $derived(
		paper
			? formatInstituteAttribution(
					paper.institute_name,
					paper.institute_origin_nexus,
					localNexusId
				)
			: { primary: '', suffix: null as string | null, title: null as string | null }
	);

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
			<a
				href="/institute/{paper.institute_id}"
				class="institute-link"
				title={authorAttribution.title ?? undefined}
			>
				<Avatar seed={paper.institute_id} size={32} />
				<span
					>{authorAttribution.primary}{#if authorAttribution.suffix}<span class="origin-suffix"
							>{authorAttribution.suffix}</span
						>{/if}</span
				>
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

		{#if paper.superseded_by}
			<div class="version-banner newer">
				A newer version of this paper exists: <a href="/paper/{paper.superseded_by}" class="mono">{paper.superseded_by}</a>
			</div>
		{/if}

		{#if paper.supersedes}
			<div class="version-banner older">
				This paper supersedes <a href="/paper/{paper.supersedes}" class="mono">{paper.supersedes}</a>
			</div>
		{/if}

		{#if paper.retracted_by}
			<div class="retraction-banner retracted">
				This paper has been retracted. See retraction notice: <a href="/paper/{paper.retracted_by}" class="mono">{paper.retracted_by}</a>
			</div>
		{/if}

		{#if paper.retracts}
			<div class="retraction-banner notice">
				This is a retraction notice for <a href="/paper/{paper.retracts}" class="mono">{paper.retracts}</a>
			</div>
		{/if}

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

		{#if paper.external_references && paper.external_references.length > 0}
			<section class="refs">
				<h2>External References</h2>
				<ul>
					{#each paper.external_references as ext}
						<li>
							{#if ext.url}
								<a href={ext.url} target="_blank" rel="noopener">{ext.title || ext.url}</a>
							{:else}
								<span>{ext.title}</span>
							{/if}
							{#if ext.doi}
								<span class="doi mono">{ext.doi}</span>
							{/if}
						</li>
					{/each}
				</ul>
			</section>
		{/if}

		{#if paper.reactions.length > 0}
			<section class="reactions">
				<h2>Reactions</h2>
				<div class="reaction-list">
					{#each paper.reactions as reaction}
						{@const rAtt = formatInstituteAttribution(
							reaction.institute_name,
							reaction.institute_origin_nexus,
							localNexusId
						)}
						<div class="reaction-item">
							<ReactionBadge type={reaction.reaction_type} />
							<a href="/institute/{reaction.institute_id}" title={rAtt.title ?? undefined}>
								{rAtt.primary}{#if rAtt.suffix}<span class="origin-suffix">{rAtt.suffix}</span>{/if}
							</a>
						</div>
					{/each}
				</div>
			</section>
		{/if}

		{#if paper.reviews && paper.reviews.length > 0}
			<section class="reviews">
				<h2>Peer Reviews</h2>
				<div class="review-list">
					{#each paper.reviews as review}
						<ReviewCard {review} {localNexusId} />
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
	.origin-suffix {
		font-weight: 600;
		color: var(--muted);
		margin-left: 0.2em;
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
	.version-banner {
		padding: 0.65rem 1rem;
		border-radius: 8px;
		font-size: 0.88rem;
		margin-bottom: 1.25rem;
	}
	.version-banner.newer {
		background: #fff5d6;
		color: #8a6d00;
		border: 1px solid #e8d590;
	}
	.version-banner.older {
		background: #e6f0ff;
		color: #2a5ea8;
		border: 1px solid #b3d1f7;
	}
	.version-banner a {
		font-weight: 600;
	}
	.retraction-banner {
		padding: 0.65rem 1rem;
		border-radius: 8px;
		font-size: 0.88rem;
		margin-bottom: 1.25rem;
		font-weight: 500;
	}
	.retraction-banner.retracted {
		background: #fce4e4;
		color: #b33030;
		border: 1px solid #f0b3b3;
	}
	.retraction-banner.notice {
		background: #f5f0fa;
		color: #6633aa;
		border: 1px solid #d4c4e8;
	}
	.retraction-banner a {
		font-weight: 600;
	}
	.doi {
		font-size: 0.78rem;
		color: var(--muted);
		margin-left: 0.5rem;
	}
	.review-list {
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
