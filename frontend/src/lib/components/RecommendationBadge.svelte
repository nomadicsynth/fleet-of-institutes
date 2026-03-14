<script lang="ts">
	let { recommendation, count = 1 }: { recommendation: string; count?: number } = $props();

	const labels: Record<string, { icon: string; label: string; cls: string }> = {
		accept: { icon: '\u2714', label: 'Accept', cls: 'accept' },
		revise: { icon: '\u270E', label: 'Revise', cls: 'revise' },
		reject: { icon: '\u2716', label: 'Reject', cls: 'reject' },
		neutral: { icon: '\u2014', label: 'Neutral', cls: 'neutral' }
	};

	const info = $derived(labels[recommendation] ?? { icon: '?', label: recommendation, cls: '' });
</script>

<span class="badge {info.cls}" title={info.label}>
	{info.icon} {info.label}
	{#if count > 1}&times;{count}{/if}
</span>

<style>
	.badge {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		font-size: 0.78rem;
		padding: 0.2rem 0.6rem;
		border-radius: 99px;
		font-weight: 600;
	}
	.accept {
		background: #e6f9e6;
		color: #1a7a1a;
	}
	.revise {
		background: #fff5d6;
		color: #8a6d00;
	}
	.reject {
		background: #fce4e4;
		color: #b33030;
	}
	.neutral {
		background: #f0f0f0;
		color: #666;
	}
</style>
