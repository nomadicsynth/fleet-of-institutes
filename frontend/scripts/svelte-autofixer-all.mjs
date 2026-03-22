#!/usr/bin/env node
/**
 * Runs `npx @sveltejs/mcp svelte-autofixer` on every *.svelte[.ts|.js] file under src/
 * and writes a JSON report for tracking (see ../svelte-autofixer-report.json).
 */
import { execFileSync } from 'node:child_process';
import { existsSync, writeFileSync } from 'node:fs';
import { readdir } from 'node:fs/promises';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const frontendRoot = join(__dirname, '..');

/** @param {string} dir */
async function collectSvelteFiles(dir, base = dir) {
	/** @type {string[]} */
	const out = [];
	const entries = await readdir(dir, { withFileTypes: true });
	for (const e of entries) {
		const p = join(dir, e.name);
		if (e.isDirectory()) {
			out.push(...(await collectSvelteFiles(p, base)));
		} else if (e.isFile() && (e.name.endsWith('.svelte') || e.name.endsWith('.svelte.ts') || e.name.endsWith('.svelte.js'))) {
			out.push(relative(base, p));
		}
	}
	return out.sort();
}

function parseAutofixerStdout(stdout) {
	const trimmed = stdout.trim();
	const lastBrace = trimmed.lastIndexOf('}');
	if (lastBrace === -1) {
		return { parseError: 'no closing brace in output', raw: trimmed };
	}
	let depth = 0;
	let start = -1;
	for (let i = lastBrace; i >= 0; i--) {
		const c = trimmed[i];
		if (c === '}') depth++;
		else if (c === '{') {
			depth--;
			if (depth === 0) {
				start = i;
				break;
			}
		}
	}
	if (start === -1) {
		return { parseError: 'could not find matching {', raw: trimmed };
	}
	const objStr = trimmed.slice(start, lastBrace + 1);
	try {
		const fn = new Function(`return (${objStr})`);
		return fn();
	} catch (e) {
		return {
			parseError: e instanceof Error ? e.message : String(e),
			rawObject: objStr,
			raw: trimmed
		};
	}
}

function resolveAutofixerCommand() {
	const localBin = join(frontendRoot, 'node_modules', '.bin', 'svelte-mcp');
	if (existsSync(localBin)) {
		return { cmd: localBin, argsPrefix: [] };
	}
	return {
		cmd: 'npx',
		argsPrefix: ['@sveltejs/mcp', 'svelte-autofixer']
	};
}

function runAutofixer(relPath) {
	const { cmd, argsPrefix } = resolveAutofixerCommand();
	const args =
		argsPrefix.length > 0
			? [...argsPrefix, relPath, '--svelte-version', '5']
			: ['svelte-autofixer', relPath, '--svelte-version', '5'];
	const stdout = execFileSync(cmd, args, {
		cwd: frontendRoot,
		encoding: 'utf8',
		maxBuffer: 10 * 1024 * 1024,
		stdio: ['ignore', 'pipe', 'pipe']
	});
	return parseAutofixerStdout(stdout);
}

const files = await collectSvelteFiles(join(frontendRoot, 'src'));

/** @type {Array<{ path: string } & Record<string, unknown>>} */
const results = [];
let filesWithIssues = 0;

for (const rel of files) {
	const parsed = runAutofixer(rel);
	const hasIssues =
		Array.isArray(parsed.issues) &&
		parsed.issues.length > 0 &&
		!parsed.parseError;
	if (hasIssues) filesWithIssues++;

	results.push({
		path: rel.replaceAll('\\', '/'),
		...parsed
	});
}

const report = {
	generatedAt: new Date().toISOString(),
	tool: '@sveltejs/mcp svelte-autofixer',
	svelteVersion: 5,
	root: 'src',
	totalFiles: files.length,
	filesWithIssues,
	files: results
};

const outFile = join(frontendRoot, 'svelte-autofixer-report.json');
writeFileSync(outFile, JSON.stringify(report, null, 2) + '\n', 'utf8');
console.log(`Wrote ${outFile} (${files.length} files, ${filesWithIssues} with issues).`);
