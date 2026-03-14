<script lang="ts">
	let { seed, size = 40 }: { seed: string; size?: number } = $props();

	function hashColor(s: string, offset = 0): string {
		let h = 0;
		for (let i = 0; i < s.length; i++) {
			h = s.charCodeAt(i) + ((h << 5) - h) + offset;
			h |= 0;
		}
		return `hsl(${Math.abs(h) % 360}, 65%, 45%)`;
	}

	const c1 = $derived(hashColor(seed, 0));
	const c2 = $derived(hashColor(seed, 99));
	const c3 = $derived(hashColor(seed, 777));
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 40 40"
	xmlns="http://www.w3.org/2000/svg"
	style="border-radius: 6px; flex-shrink: 0;"
>
	<rect width="40" height="40" fill={c1} />
	<circle cx="12" cy="14" r="9" fill={c2} opacity="0.7" />
	<rect x="18" y="16" width="16" height="16" rx="3" fill={c3} opacity="0.6" />
	<circle cx="28" cy="10" r="6" fill={c2} opacity="0.5" />
</svg>
