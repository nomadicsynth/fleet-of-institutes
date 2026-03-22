<script lang="ts">
	import { formatInstituteAttribution, type Review } from '$lib/api';
	import Avatar from './Avatar.svelte';
	import RecommendationBadge from './RecommendationBadge.svelte';

	let { review, localNexusId }: { review: Review; localNexusId: string } = $props();

	const attribution = $derived(
		formatInstituteAttribution(
			review.institute_name,
			review.institute_origin_nexus,
			localNexusId
		)
	);

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleDateString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric'
		});
	}

	const confidenceLabel: Record<string, string> = {
		high: 'High confidence',
		medium: 'Medium confidence',
		low: 'Low confidence'
	};
</script>

<div class="review-card">
	<div class="review-header">
		<a
			href="/institute/{review.institute_id}"
			class="reviewer"
			title={attribution.title ?? undefined}
		>
			<Avatar seed={review.institute_id} size={28} />
			<span class="reviewer-name"
				>{attribution.primary}{#if attribution.suffix}<span class="origin-suffix"
						>{attribution.suffix}</span
					>{/if}</span
			>
		</a>
		<div class="review-meta">
			<RecommendationBadge recommendation={review.recommendation} />
			<span class="confidence">{confidenceLabel[review.confidence] ?? review.confidence}</span>
			<span class="date">{formatDate(review.created_at)}</span>
		</div>
	</div>

	<div class="review-body">
		{#if review.summary}
			<div class="review-section">
				<h4>Summary</h4>
				<p>{review.summary}</p>
			</div>
		{/if}

		{#if review.strengths}
			<div class="review-section">
				<h4>Strengths</h4>
				<p>{review.strengths}</p>
			</div>
		{/if}

		{#if review.weaknesses}
			<div class="review-section">
				<h4>Weaknesses</h4>
				<p>{review.weaknesses}</p>
			</div>
		{/if}

		{#if review.questions}
			<div class="review-section">
				<h4>Questions</h4>
				<p>{review.questions}</p>
			</div>
		{/if}
	</div>
</div>

<style>
	.review-card {
		background: var(--card-bg);
		border: 1px solid var(--border);
		border-radius: 10px;
		padding: 1.25rem;
	}
	.review-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
		flex-wrap: wrap;
		gap: 0.5rem;
	}
	.reviewer {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		text-decoration: none;
	}
	.reviewer-name {
		font-weight: 600;
		font-size: 0.9rem;
		color: var(--accent);
	}
	.reviewer:hover .reviewer-name {
		text-decoration: underline;
	}
	.origin-suffix {
		font-weight: 500;
		color: var(--muted);
		margin-left: 0.2em;
	}
	.review-meta {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-wrap: wrap;
	}
	.confidence {
		font-size: 0.78rem;
		color: var(--muted);
		font-style: italic;
	}
	.date {
		font-size: 0.78rem;
		color: var(--muted);
	}
	.review-body {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	.review-section h4 {
		font-size: 0.82rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--muted);
		margin-bottom: 0.25rem;
	}
	.review-section p {
		font-size: 0.92rem;
		line-height: 1.6;
		white-space: pre-wrap;
	}
</style>
