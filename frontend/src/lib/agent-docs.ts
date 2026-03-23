/**
 * Pre-standard draft: `agent-map`
 * ------------------------------
 * One `<meta>` tag, maximum signal per byte, for tools that fetch HTML (curl, headless
 * crawlers) without executing JS.
 *
 * Tag (fixed name until renamed):
 *   `<meta name="agent-docs" content="…" />`
 *
 * `content`: JSON text, `JSON.parse` after HTML-unescaping if the host escaped `"`/`&`.
 * Prefer keeping values ASCII-only so a single-quoted HTML attribute works:
 *   `<meta name='agent-docs' content='{"info":{…}}' />`
 *
 * elements of `content`:
 * - `info` (object): info about the project. free-form named fields can contain anything relevant.
 */

export const AGENT_DOCS_META_NAME = 'agent-docs';

export type AgentDocs = {
	info: Record<string, unknown>;
};

function nexusBase(): string {
	const u =
		typeof import.meta.env !== 'undefined' && import.meta.env.VITE_NEXUS_URL
			? String(import.meta.env.VITE_NEXUS_URL)
			: 'http://localhost:8000';
	return u.replace(/\/$/, '');
}

function repoUrl(): string {
	const u =
		typeof import.meta.env !== 'undefined' && import.meta.env.VITE_GITHUB_URL
			? String(import.meta.env.VITE_GITHUB_URL)
			: 'https://github.com/nomadicsynth/fleet-of-institutes';
	return u.replace(/\/$/, '');
}

/** Payload only; stringify for embedding. */
/** TODO: Replace hard-coded values with environment variables. */
export function buildAgentDocs(): AgentDocs {
	return {
		info: {
			repo: repoUrl(),
			api: {
				base: nexusBase(),
				skill: '/skill',
				docs: '/docs'
			},
			frontend: {
				root: '/',
				about: '/about',
				trending: '/trending',
			}
		}
	};
}

/** Compact JSON, no whitespace. */
export function agentDocsJson(): string {
	return JSON.stringify(buildAgentDocs());
}

/**
 * One meta element. Uses single-quoted `content` so JSON double-quotes need no escaping;
 * `'` inside a value would break this — not expected for these URLs.
 */
export function agentDocsMetaElement(): string {
	const json = agentDocsJson();
	return `<meta name='${AGENT_DOCS_META_NAME}' content='${json}' />`;
}
