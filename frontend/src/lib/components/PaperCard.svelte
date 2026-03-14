<script lang="ts">
	import type { PaperSummary } from '$lib/api';
	import Avatar from './Avatar.svelte';

	let { paper }: { paper: PaperSummary } = $props();

	function timeAgo(iso: string): string {
		const diff = Date.now() - new Date(iso).getTime();
		const mins = Math.floor(diff / 60000);
		if (mins < 60) return `${mins}m ago`;
		const hrs = Math.floor(mins / 60);
		if (hrs < 24) return `${hrs}h ago`;
		const days = Math.floor(hrs / 24);
		return `${days}d ago`;
	}

	const reactionTotal = $derived(
		Object.values(paper.reaction_counts).reduce((a, b) => a + b, 0)
	);
	const tags = $derived(paper.tags ? paper.tags.split(',').map((t) => t.trim()) : []);
</script>

<div class="card">
	<div class="card-header">
		<Avatar seed={paper.institute_id} size={36} />
		<div class="meta">
			<a href="/institute/{paper.institute_id}" class="institute-name">
				{paper.institute_name}
			</a>
			<span class="timestamp">{paper.id} &middot; {timeAgo(paper.timestamp)}</span>
		</div>
	</div>

	<a href="/paper/{paper.id}" class="title-link"><h3 class="title">{paper.title}</h3></a>
	<p class="summary">{paper.summary}</p>

	<div class="card-footer">
		<div class="tags">
			{#each tags as tag}
				<span class="tag">{tag}</span>
			{/each}
		</div>
		<div class="stats">
			{#if paper.citation_count > 0}
				<span class="stat" title="Citations">&#128279; {paper.citation_count}</span>
			{/if}
			{#if reactionTotal > 0}
				<span class="stat" title="Reactions">&#9733; {reactionTotal}</span>
			{/if}
		</div>
	</div>
</div>

<style>
	.card {
		display: block;
		background: var(--card-bg, #fff);
		border: 1px solid var(--border, #e2e2e2);
		border-radius: 10px;
		padding: 1.25rem;
		color: inherit;
		transition: box-shadow 0.15s, border-color 0.15s;
	}
	.card:hover {
		border-color: var(--accent, #4a6cf7);
		box-shadow: 0 2px 12px rgba(74, 108, 247, 0.08);
	}
	.title-link {
		text-decoration: none;
		color: inherit;
	}
	.title-link:hover .title {
		color: var(--accent, #4a6cf7);
	}
	.card-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 0.75rem;
	}
	.meta {
		display: flex;
		flex-direction: column;
	}
	.institute-name {
		font-weight: 600;
		font-size: 0.9rem;
		color: var(--accent, #4a6cf7);
		text-decoration: none;
	}
	.institute-name:hover {
		text-decoration: underline;
	}
	.timestamp {
		font-size: 0.78rem;
		color: var(--muted, #888);
		font-family: 'JetBrains Mono', 'Fira Code', monospace;
	}
	.title {
		margin: 0 0 0.5rem;
		font-size: 1.1rem;
		line-height: 1.35;
	}
	.summary {
		margin: 0 0 0.75rem;
		font-size: 0.92rem;
		color: var(--text-secondary, #555);
		line-height: 1.5;
	}
	.card-footer {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
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
		background: var(--tag-bg, #f0f0f0);
		color: var(--tag-text, #555);
		font-family: 'JetBrains Mono', 'Fira Code', monospace;
	}
	.stats {
		display: flex;
		gap: 0.75rem;
		font-size: 0.82rem;
		color: var(--muted, #888);
	}
	.stat {
		white-space: nowrap;
	}
</style>
