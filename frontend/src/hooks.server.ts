import type { Handle } from '@sveltejs/kit';
import { AGENT_DOCS_META_NAME, agentDocsMetaElement } from '$lib/agent-docs';

/** Inject pre-standard `agent-docs` meta into every server-rendered HTML shell. */
export const handle: Handle = async ({ event, resolve }) => {
	const meta = agentDocsMetaElement();
	let injected = false;
	return resolve(event, {
		transformPageChunk: ({ html, done }) => {
			if (injected || html.includes(AGENT_DOCS_META_NAME)) return html;
			if (html.includes('<meta charset="utf-8" />')) {
				injected = true;
				return html.replace('<meta charset="utf-8" />', `<meta charset="utf-8" />\n\t\t${meta}`);
			}
			if (done && html.includes('</head>')) {
				injected = true;
				return html.replace('</head>', `\t\t${meta}\n\t</head>`);
			}
			return html;
		}
	});
};
