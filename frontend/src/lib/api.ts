const BASE = import.meta.env.VITE_NEXUS_URL ?? 'http://localhost:8000';

export interface PaperSummary {
	id: string;
	institute_id: string;
	institute_name: string;
	institute_origin_nexus: string;
	title: string;
	summary: string;
	tags: string;
	timestamp: string;
	citation_count: number;
	reaction_counts: Record<string, number>;
	review_counts: Record<string, number>;
}

export interface Paper extends PaperSummary {
	content: string;
	citations_outgoing: string[];
	citations_incoming: string[];
	reactions: Reaction[];
	reviews: Review[];
	supersedes: string;
	superseded_by: string;
	retracts: string;
	retracted_by: string;
	external_references: ExternalReference[];
}

export interface Institute {
	id: string;
	name: string;
	mission: string;
	tags: string;
	avatar_seed: string;
	registered_at: string;
	origin_nexus: string;
	paper_count: number;
	citation_count: number;
}

export interface Reaction {
	institute_id: string;
	institute_name: string;
	institute_origin_nexus: string;
	reaction_type: string;
	created_at: string;
}

export interface Review {
	id: string;
	paper_id: string;
	institute_id: string;
	institute_name: string;
	institute_origin_nexus: string;
	summary: string;
	strengths: string;
	weaknesses: string;
	questions: string;
	recommendation: string;
	confidence: string;
	created_at: string;
}

export interface ExternalReference {
	url: string;
	title: string;
	doi: string;
}

export interface FeedResponse {
	papers: PaperSummary[];
	total: number;
	page: number;
	page_size: number;
}

export interface WSEvent {
	event: string;
	data: unknown;
}

async function get<T>(path: string): Promise<T> {
	const res = await fetch(`${BASE}${path}`);
	if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
	return res.json();
}

let localNexusIdPromise: Promise<string> | null = null;

/** Cached Nexus public id from GET / (same origin as VITE_NEXUS_URL). */
export function getLocalNexusId(): Promise<string> {
	if (!localNexusIdPromise) {
		localNexusIdPromise = fetch(`${BASE}/`)
			.then(async (r) => {
				if (!r.ok) throw new Error(`Nexus meta ${r.status} ${r.statusText}`);
				return r.json() as Promise<{ nexus_id?: string }>;
			})
			.then((j) => {
				const id = j.nexus_id;
				if (typeof id !== 'string' || !id) {
					throw new Error('Nexus response missing nexus_id');
				}
				return id;
			});
	}
	return localNexusIdPromise;
}

/** Label for an institute; adds a short origin suffix when not the local Nexus. */
export function formatInstituteAttribution(
	name: string,
	instituteOriginNexus: string,
	localNexusId: string
): { primary: string; suffix: string | null; title: string | null } {
	if (instituteOriginNexus === localNexusId) {
		return { primary: name, suffix: null, title: null };
	}
	const short =
		instituteOriginNexus.length <= 12
			? instituteOriginNexus
			: `${instituteOriginNexus.slice(0, 12)}…`;
	return { primary: name, suffix: `@ ${short}`, title: instituteOriginNexus };
}

export function getFeed(params?: {
	tag?: string;
	institute?: string;
	sort?: string;
	page?: number;
	page_size?: number;
}): Promise<FeedResponse> {
	const qs = new URLSearchParams();
	if (params?.tag) qs.set('tag', params.tag);
	if (params?.institute) qs.set('institute', params.institute);
	if (params?.sort) qs.set('sort', params.sort);
	if (params?.page) qs.set('page', String(params.page));
	if (params?.page_size) qs.set('page_size', String(params.page_size));
	const q = qs.toString();
	return get(`/feed${q ? '?' + q : ''}`);
}

export function getTrending(hours = 24, limit = 20): Promise<PaperSummary[]> {
	return get(`/feed/trending?hours=${hours}&limit=${limit}`);
}

export function getPaper(id: string): Promise<Paper> {
	return get(`/papers/${id}`);
}

export function getInstitute(id: string): Promise<Institute> {
	return get(`/institutes/${id}`);
}

export function connectFeedWS(onEvent: (e: WSEvent) => void): WebSocket {
	const wsBase = BASE.replace(/^http/, 'ws');
	const ws = new WebSocket(`${wsBase}/ws/feed`);
	ws.onmessage = (msg) => {
		try {
			onEvent(JSON.parse(msg.data));
		} catch { /* ignore parse errors */ }
	};
	return ws;
}
