<script lang="ts">
	let { type, count = 1 }: { type: string; count?: number } = $props();

	const labels: Record<string, { icon: string; label: string; cls: string }> = {
		endorse: { icon: '\u2714', label: 'Endorsed', cls: 'endorse' },
		dispute: { icon: '\u2716', label: 'Disputed', cls: 'dispute' },
		landmark: { icon: '\u2605', label: 'Landmark', cls: 'landmark' },
		retract: { icon: '\u21A9', label: 'Retracted', cls: 'retract' }
	};

	const info = $derived(labels[type] ?? { icon: '?', label: type, cls: '' });
</script>

<span class="badge {info.cls}" title={info.label}>
	{info.icon}
	{#if count > 1}{count}{/if}
</span>

<style>
	.badge {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.78rem;
		padding: 0.2rem 0.55rem;
		border-radius: 99px;
		font-weight: 600;
	}
	.endorse {
		background: #e6f9e6;
		color: #1a7a1a;
	}
	.dispute {
		background: #fce4e4;
		color: #b33030;
	}
	.landmark {
		background: #fff5d6;
		color: #8a6d00;
	}
	.retract {
		background: #f0e6ff;
		color: #6633aa;
	}
</style>
