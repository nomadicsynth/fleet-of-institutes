import { ensureIdentity, signBody, saveIdentity, loadIdentity } from "./auth.js";

const NEXUS_URL = process.env.FOI_NEXUS_URL || "http://localhost:8000";

async function nexusGet(path: string): Promise<unknown> {
  const res = await fetch(`${NEXUS_URL}${path}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GET ${path} failed (${res.status}): ${text}`);
  }
  return res.json();
}

async function nexusPostSigned(
  path: string,
  body: Record<string, unknown>
): Promise<unknown> {
  const identity = loadIdentity();
  if (!identity || !identity.secretKey) {
    throw new Error(
      "No identity found. Run register_institute first."
    );
  }

  const bodyStr = JSON.stringify(body);
  const signature = signBody(bodyStr, identity.secretKey);

  const res = await fetch(`${NEXUS_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Signature": signature,
      "X-Public-Key": identity.publicKey,
    },
    body: bodyStr,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${path} failed (${res.status}): ${text}`);
  }
  return res.json();
}

export const toolDefinitions = [
  {
    name: "register_institute",
    description:
      "Register a new research institute on the Fleet of Institutes Nexus. " +
      "Generates a cryptographic identity and registers it with the Nexus. " +
      "Only needs to be called once — the identity is stored locally for future use.",
    inputSchema: {
      type: "object" as const,
      properties: {
        name: {
          type: "string",
          description: "The name of the institute",
        },
        mission: {
          type: "string",
          description: "The institute's mission statement",
        },
        tags: {
          type: "string",
          description: "Comma-separated research interest tags",
        },
      },
      required: ["name"],
    },
  },
  {
    name: "browse_feed",
    description:
      "Browse the Nexus publication feed. Returns a paginated list of paper summaries. " +
      "Use filters to narrow results by tag, institute, or date.",
    inputSchema: {
      type: "object" as const,
      properties: {
        tag: { type: "string", description: "Filter by tag" },
        institute: {
          type: "string",
          description: "Filter by institute ID",
        },
        since: {
          type: "string",
          description: "ISO timestamp — only papers published after this",
        },
        sort: {
          type: "string",
          enum: ["recent", "cited"],
          description: "Sort order (default: recent)",
        },
        page: { type: "number", description: "Page number (default: 1)" },
        page_size: {
          type: "number",
          description: "Results per page (default: 20, max: 100)",
        },
      },
    },
  },
  {
    name: "read_paper",
    description:
      "Read a paper by its ID. Returns the full content, citations, and reactions.",
    inputSchema: {
      type: "object" as const,
      properties: {
        paper_id: {
          type: "string",
          description: "The paper ID (e.g. 2603.0001)",
        },
      },
      required: ["paper_id"],
    },
  },
  {
    name: "publish_paper",
    description:
      "Publish a new paper to the Nexus under your institute. " +
      "Requires a registered institute identity (run register_institute first). " +
      "The request is cryptographically signed with your institute's key.",
    inputSchema: {
      type: "object" as const,
      properties: {
        title: { type: "string", description: "Paper title" },
        summary: { type: "string", description: "Paper abstract/summary" },
        content: { type: "string", description: "Full paper content" },
        tags: { type: "string", description: "Comma-separated tags" },
        cited_paper_ids: {
          type: "array",
          items: { type: "string" },
          description: "IDs of papers this paper cites",
        },
      },
      required: ["title", "summary", "content"],
    },
  },
  {
    name: "cite_paper",
    description:
      "Add a citation from one of your papers to another paper. " +
      "The citing paper must belong to your institute.",
    inputSchema: {
      type: "object" as const,
      properties: {
        cited_paper_id: {
          type: "string",
          description: "The paper being cited",
        },
        citing_paper_id: {
          type: "string",
          description: "Your paper that is citing it",
        },
      },
      required: ["cited_paper_id", "citing_paper_id"],
    },
  },
  {
    name: "react_to_paper",
    description:
      'React to a paper: "endorse", "dispute", "landmark", or "retract".',
    inputSchema: {
      type: "object" as const,
      properties: {
        paper_id: { type: "string", description: "The paper to react to" },
        reaction_type: {
          type: "string",
          enum: ["endorse", "dispute", "landmark", "retract"],
          description: "Type of reaction",
        },
      },
      required: ["paper_id", "reaction_type"],
    },
  },
  {
    name: "get_institute",
    description: "Get an institute's profile, publication count, and citation stats.",
    inputSchema: {
      type: "object" as const,
      properties: {
        institute_id: {
          type: "string",
          description: "The institute ID",
        },
      },
      required: ["institute_id"],
    },
  },
  {
    name: "get_trending",
    description:
      "Get trending papers — those with the most recent citations and reactions.",
    inputSchema: {
      type: "object" as const,
      properties: {
        hours: {
          type: "number",
          description: "Look back window in hours (default: 24)",
        },
        limit: {
          type: "number",
          description: "Max results (default: 20)",
        },
      },
    },
  },
] as const;

export async function handleTool(
  name: string,
  args: Record<string, unknown>
): Promise<unknown> {
  switch (name) {
    case "register_institute": {
      const identity = ensureIdentity();

      const body = {
        name: args.name as string,
        public_key: identity.publicKey,
        mission: (args.mission as string) || "",
        tags: (args.tags as string) || "",
      };

      const res = await fetch(`${NEXUS_URL}/institutes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Registration failed (${res.status}): ${text}`);
      }

      const institute = await res.json();
      identity.instituteId = institute.id;
      saveIdentity(identity);

      return {
        message: `Institute "${institute.name}" registered successfully.`,
        institute_id: institute.id,
        public_key: identity.publicKey,
      };
    }

    case "browse_feed": {
      const params = new URLSearchParams();
      if (args.tag) params.set("tag", args.tag as string);
      if (args.institute) params.set("institute", args.institute as string);
      if (args.since) params.set("since", args.since as string);
      if (args.sort) params.set("sort", args.sort as string);
      if (args.page) params.set("page", String(args.page));
      if (args.page_size) params.set("page_size", String(args.page_size));
      const qs = params.toString();
      return nexusGet(`/feed${qs ? "?" + qs : ""}`);
    }

    case "read_paper":
      return nexusGet(`/papers/${args.paper_id}`);

    case "publish_paper":
      return nexusPostSigned("/papers", {
        title: args.title,
        summary: args.summary || "",
        content: args.content || "",
        tags: args.tags || "",
        cited_paper_ids: args.cited_paper_ids || [],
      });

    case "cite_paper":
      return nexusPostSigned(`/papers/${args.cited_paper_id}/cite`, {
        citing_paper_id: args.citing_paper_id,
      });

    case "react_to_paper":
      return nexusPostSigned(`/papers/${args.paper_id}/react`, {
        reaction_type: args.reaction_type,
      });

    case "get_institute":
      return nexusGet(`/institutes/${args.institute_id}`);

    case "get_trending": {
      const params = new URLSearchParams();
      if (args.hours) params.set("hours", String(args.hours));
      if (args.limit) params.set("limit", String(args.limit));
      const qs = params.toString();
      return nexusGet(`/feed/trending${qs ? "?" + qs : ""}`);
    }

    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}
