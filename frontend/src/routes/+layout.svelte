<script lang="ts">
	import '../app.css';
	let { children } = $props();
</script>

<header>
	<div class="header-inner">
		<a href="/" class="logo">
			<span class="logo-icon">&#x1D4D5;</span>
			Fleet of Institutes
		</a>
		<nav>
			<a href="/">Feed</a>
			<a href="/trending">Trending</a>
		</nav>
	</div>
</header>

<main>
	{@render children()}
</main>

<style>
	header {
		position: sticky;
		top: 0;
		z-index: 100;
		background: var(--header-bg);
		border-bottom: 1px solid var(--border);
		backdrop-filter: blur(12px);
	}
	.header-inner {
		max-width: 52rem;
		margin: 0 auto;
		padding: 0.75rem 1.5rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}
	.logo {
		font-weight: 700;
		font-size: 1.15rem;
		text-decoration: none;
		color: var(--text);
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.logo-icon {
		font-size: 1.4rem;
	}
	nav {
		display: flex;
		gap: 1.5rem;
	}
	nav a {
		text-decoration: none;
		font-size: 0.9rem;
		font-weight: 500;
		color: var(--muted);
		transition: color 0.15s;
	}
	nav a:hover {
		color: var(--accent);
	}
	main {
		max-width: 52rem;
		margin: 0 auto;
		padding: 1.5rem;
	}
</style>
