/**
 * GBrain Bridge Extension for Copilot CLI
 *
 * Exposes Tony's `gbrain` personal knowledge brain as first-class tools to
 * every Copilot CLI session and cron-dispatched agent. Read-and-put only —
 * `delete` is intentionally not exposed.
 *
 * Tools registered:
 *   - gbrain_query  : hybrid search (RRF + expansion), the default retrieval tool
 *   - gbrain_search : keyword (tsvector) search
 *   - gbrain_get    : fetch a single page by slug
 *   - gbrain_put    : write/update a page (stdin), with optional embedding
 *   - gbrain_list   : list pages by type/tag
 *
 * Safety rails (hardcoded, non-negotiable):
 *   - Refuses to write any slug under notes/records/private, notes/records/secrets,
 *     or anything containing secrets|credentials|cookies|tokens|api_keys|oauth|.env
 *   - Refuses absolute-path slugs (must be brain-repo-relative)
 *   - Never spawns a shell — uses `spawn` with array argv only
 *   - 30s default per-command timeout (override via `timeout_ms`, capped at 120s)
 *   - `delete` is never exposed
 *   - All spawns run with cwd = /home/tonyxu/brain
 */
import { spawn } from "node:child_process";
import { writeFileSync, openSync, closeSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { joinSession } from "@github/copilot-sdk/extension";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const GBRAIN_BIN = process.env.GBRAIN_BIN || "/home/tonyxu/.local/bin/gbrain";
const BRAIN_CWD = process.env.GBRAIN_CWD || "/home/tonyxu/brain";
const DEFAULT_TIMEOUT_MS = 30_000;
const MAX_TIMEOUT_MS = 120_000;
const MAX_PUT_BYTES = 512 * 1024; // 512KB per page is plenty

// Hardcoded blocklist — slugs matching any of these are refused for writes.
const SLUG_BLOCK_PATTERNS = [
  /^notes\/records\/private(\/|$)/i,
  /^notes\/records\/secrets(\/|$)/i,
  /(^|\/|-|_)secrets?(\/|-|_|$)/i,
  /(^|\/|-|_)credentials?(\/|-|_|$)/i,
  /(^|\/|-|_)cookies?(\/|-|_|$)/i,
  /(^|\/|-|_)tokens?(\/|-|_|$)/i,
  /(^|\/|-|_)api[-_]?keys?(\/|-|_|$)/i,
  /(^|\/|-|_)oauth(\/|-|_|$)/i,
  /(^|\/|-|_)\.env(\/|$)/i,
  /(^|\/|-|_)passwords?(\/|-|_|$)/i,
];

function isBlockedSlug(slug) {
  if (typeof slug !== "string" || !slug) return "slug must be a non-empty string";
  if (slug.startsWith("/")) return "absolute-path slugs are not allowed; use a brain-relative slug";
  if (slug.includes("..")) return "slug must not contain '..'";
  if (slug.length > 512) return "slug too long";
  for (const re of SLUG_BLOCK_PATTERNS) {
    if (re.test(slug)) return `slug matches blocked pattern ${re} (private/secrets/credentials/tokens are off-limits)`;
  }
  return null;
}

function clampTimeout(t) {
  const n = Number(t);
  if (!Number.isFinite(n) || n <= 0) return DEFAULT_TIMEOUT_MS;
  return Math.min(Math.max(n, 1000), MAX_TIMEOUT_MS);
}

function clampLimit(n, def, max) {
  const x = Number(n);
  if (!Number.isFinite(x) || x <= 0) return def;
  return Math.min(Math.floor(x), max);
}

// ---------------------------------------------------------------------------
// spawn wrapper — no shell, captures stdout/stderr, enforces timeout.
//
// gbrain (Bun-compiled) reads stdin by opening /dev/stdin as a file, which
// fails with ENXIO when fd 0 is a Node pipe. To support `gbrain put` we accept
// a `stdinFile` path; the file is opened with fs.openSync('r') and the FD is
// passed as the child's stdin so `/dev/stdin` resolves to a real file.
// ---------------------------------------------------------------------------
function runGbrain(args, { stdinFile = null, timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  return new Promise((resolve) => {
    let stdout = "";
    let stderr = "";
    let timedOut = false;
    let stdinFd = null;

    if (stdinFile) {
      try {
        stdinFd = openSync(stdinFile, "r");
      } catch (err) {
        resolve({ ok: false, code: -1, stdout: "", stderr: `failed to open stdin file: ${err.message}`, timedOut: false });
        return;
      }
    }

    const child = spawn(GBRAIN_BIN, args, {
      cwd: BRAIN_CWD,
      env: process.env,
      stdio: [stdinFd !== null ? stdinFd : "ignore", "pipe", "pipe"],
      shell: false,
    });

    const timer = setTimeout(() => {
      timedOut = true;
      try { child.kill("SIGKILL"); } catch { /* noop */ }
    }, timeoutMs);

    child.stdout.on("data", (b) => { stdout += b.toString("utf8"); });
    child.stderr.on("data", (b) => { stderr += b.toString("utf8"); });

    const cleanup = () => {
      if (stdinFd !== null) {
        try { closeSync(stdinFd); } catch { /* noop */ }
      }
    };

    child.on("error", (err) => {
      clearTimeout(timer);
      cleanup();
      resolve({ ok: false, code: -1, stdout, stderr, error: err.message, timedOut });
    });

    child.on("close", (code) => {
      clearTimeout(timer);
      cleanup();
      resolve({ ok: code === 0 && !timedOut, code, stdout, stderr, timedOut });
    });
  });
}

// ---------------------------------------------------------------------------
// Output parsers
// ---------------------------------------------------------------------------
// `gbrain query/search` lines look like:
//   [0.3964] sources/gmail/digests/2026-04-30 -- 💹 Tony and Han Daily Digest ...
// Snippets may wrap; the slug+score line is the anchor.
function parseSearchHits(stdout, limit) {
  const lines = stdout.split("\n");
  const hits = [];
  let current = null;
  const hitRe = /^\[([0-9.]+)\]\s+(\S+)\s+--\s*(.*)$/;
  for (const raw of lines) {
    const line = raw.replace(/\r$/, "");
    const m = line.match(hitRe);
    if (m) {
      if (current) hits.push(current);
      current = {
        score: Number(m[1]),
        slug: m[2],
        snippet: m[3],
      };
    } else if (current && line.trim()) {
      // Continuation lines belong to the previous hit's snippet.
      current.snippet += (current.snippet ? "\n" : "") + line;
    }
  }
  if (current) hits.push(current);
  // Trim snippets to keep results compact.
  for (const h of hits) {
    if (h.snippet && h.snippet.length > 400) h.snippet = h.snippet.slice(0, 400) + "…";
  }
  if (Number.isFinite(limit) && limit > 0) return hits.slice(0, limit);
  return hits;
}

// `gbrain list` lines look like:
//   2026-06-17\tnote\tSun May 17\tCalendar Digest
function parseListLines(stdout, limit) {
  const out = [];
  for (const raw of stdout.split("\n")) {
    const line = raw.replace(/\r$/, "").trim();
    if (!line) continue;
    const parts = line.split("\t");
    if (parts.length >= 2) {
      out.push({
        slug: parts[0],
        type: parts[1] || "",
        updated: parts[2] || "",
        title: parts.slice(3).join("\t") || "",
      });
    } else {
      out.push({ raw: line });
    }
    if (Number.isFinite(limit) && limit > 0 && out.length >= limit) break;
  }
  return out;
}

function truncateForLlm(s, max = 8000) {
  if (typeof s !== "string") return s;
  if (s.length <= max) return s;
  return s.slice(0, max) + `\n…[truncated ${s.length - max} chars]`;
}

// ---------------------------------------------------------------------------
// Tool handlers
// ---------------------------------------------------------------------------
async function handleQuery(args) {
  const question = (args?.question ?? "").toString().trim();
  if (!question) return { textResultForLlm: "gbrain_query: 'question' is required", resultType: "failure" };
  const limit = clampLimit(args?.limit, 8, 50);
  const timeoutMs = clampTimeout(args?.timeout_ms);

  const cliArgs = ["query", question, "--limit", String(limit)];
  if (args?.no_expand) cliArgs.push("--no-expand");

  const r = await runGbrain(cliArgs, { timeoutMs });
  if (!r.ok) {
    if (r.timedOut) return { textResultForLlm: `gbrain_query timed out after ${timeoutMs}ms`, resultType: "failure" };
    return { textResultForLlm: `gbrain_query failed (exit ${r.code}): ${truncateForLlm(r.stderr || r.stdout, 1500)}`, resultType: "failure" };
  }
  const hits = parseSearchHits(r.stdout, limit);
  return {
    textResultForLlm: hits.length
      ? `gbrain_query "${question}" — ${hits.length} hit(s)\n` + JSON.stringify(hits, null, 2)
      : `gbrain_query "${question}" — no hits`,
  };
}

async function handleSearch(args) {
  const query = (args?.query ?? "").toString().trim();
  if (!query) return { textResultForLlm: "gbrain_search: 'query' is required", resultType: "failure" };
  const limit = clampLimit(args?.limit, 10, 50);
  const timeoutMs = clampTimeout(args?.timeout_ms);

  const r = await runGbrain(["search", query, "--limit", String(limit)], { timeoutMs });
  if (!r.ok) {
    if (r.timedOut) return { textResultForLlm: `gbrain_search timed out after ${timeoutMs}ms`, resultType: "failure" };
    return { textResultForLlm: `gbrain_search failed (exit ${r.code}): ${truncateForLlm(r.stderr || r.stdout, 1500)}`, resultType: "failure" };
  }
  const hits = parseSearchHits(r.stdout, limit);
  return {
    textResultForLlm: hits.length
      ? `gbrain_search "${query}" — ${hits.length} hit(s)\n` + JSON.stringify(hits, null, 2)
      : `gbrain_search "${query}" — no hits`,
  };
}

async function handleGet(args) {
  const slug = (args?.slug ?? "").toString().trim();
  if (!slug) return { textResultForLlm: "gbrain_get: 'slug' is required", resultType: "failure" };
  if (slug.startsWith("/") || slug.includes("..")) {
    return { textResultForLlm: "gbrain_get: slug must be brain-relative and not contain '..'", resultType: "failure" };
  }
  const timeoutMs = clampTimeout(args?.timeout_ms);
  const r = await runGbrain(["get", slug], { timeoutMs });
  if (!r.ok) {
    if (r.timedOut) return { textResultForLlm: `gbrain_get timed out after ${timeoutMs}ms`, resultType: "failure" };
    return { textResultForLlm: `gbrain_get failed (exit ${r.code}): ${truncateForLlm(r.stderr || r.stdout, 1500)}`, resultType: "failure" };
  }
  return { textResultForLlm: truncateForLlm(r.stdout, 16_000) };
}

async function handlePut(args) {
  const slug = (args?.slug ?? "").toString().trim();
  const content = args?.content;
  if (!slug) return { textResultForLlm: "gbrain_put: 'slug' is required", resultType: "failure" };
  if (typeof content !== "string" || !content.length) {
    return { textResultForLlm: "gbrain_put: 'content' (string) is required", resultType: "failure" };
  }
  const blocked = isBlockedSlug(slug);
  if (blocked) {
    return {
      textResultForLlm: `gbrain_put REFUSED: ${blocked}. Private/secrets/credentials/tokens are off-limits for the bridge.`,
      resultType: "failure",
    };
  }
  if (Buffer.byteLength(content, "utf8") > MAX_PUT_BYTES) {
    return { textResultForLlm: `gbrain_put: content exceeds ${MAX_PUT_BYTES} bytes`, resultType: "failure" };
  }
  const timeoutMs = clampTimeout(args?.timeout_ms);

  // Write content to a temp file and pass its fd as stdin — see runGbrain notes.
  const tmpDir = mkdtempSync(join(tmpdir(), "gbrain-put-"));
  const tmpFile = join(tmpDir, "page.md");
  let putR;
  try {
    writeFileSync(tmpFile, content, "utf8");
    putR = await runGbrain(["put", slug], { stdinFile: tmpFile, timeoutMs });
  } finally {
    try { rmSync(tmpDir, { recursive: true, force: true }); } catch { /* noop */ }
  }
  if (!putR.ok) {
    if (putR.timedOut) return { textResultForLlm: `gbrain_put timed out after ${timeoutMs}ms`, resultType: "failure" };
    return { textResultForLlm: `gbrain_put failed (exit ${putR.code}): ${truncateForLlm(putR.stderr || putR.stdout, 1500)}`, resultType: "failure" };
  }

  let embedNote = "";
  if (args?.embed) {
    const embedR = await runGbrain(["embed", slug], { timeoutMs });
    if (!embedR.ok) {
      embedNote = `\n(embed step failed: ${truncateForLlm(embedR.stderr || embedR.stdout, 500)})`;
    } else {
      embedNote = `\nembedded.`;
    }
  }
  return {
    textResultForLlm: `gbrain_put ok: ${slug}${embedNote}\nstdout:\n${truncateForLlm(putR.stdout, 2000)}`,
  };
}

async function handleList(args) {
  const limit = clampLimit(args?.limit, 25, 200);
  const cliArgs = ["list", "--limit", String(limit)];
  if (args?.type) cliArgs.push("--type", String(args.type));
  if (args?.tag) cliArgs.push("--tag", String(args.tag));
  const timeoutMs = clampTimeout(args?.timeout_ms);
  const r = await runGbrain(cliArgs, { timeoutMs });
  if (!r.ok) {
    if (r.timedOut) return { textResultForLlm: `gbrain_list timed out after ${timeoutMs}ms`, resultType: "failure" };
    return { textResultForLlm: `gbrain_list failed (exit ${r.code}): ${truncateForLlm(r.stderr || r.stdout, 1500)}`, resultType: "failure" };
  }
  const rows = parseListLines(r.stdout, limit);
  return {
    textResultForLlm: rows.length
      ? `gbrain_list — ${rows.length} row(s)\n` + JSON.stringify(rows, null, 2)
      : "gbrain_list — no rows",
  };
}

// ---------------------------------------------------------------------------
// Register with Copilot CLI
// ---------------------------------------------------------------------------
await joinSession({
  tools: [
    {
      name: "gbrain_query",
      description:
        "Hybrid search (vector + keyword + multi-query expansion via RRF) over Tony's gbrain " +
        "personal knowledge brain at /home/tonyxu/brain. Returns ranked slug+snippet hits. " +
        "Use this BEFORE producing recommendations for Tony so the assistant is not knowledge-isolated " +
        "per session — pull recent memo/limemo/activity/email digests/calendar context first.",
      parameters: {
        type: "object",
        properties: {
          question: { type: "string", description: "Natural-language question or topic to search." },
          no_expand: { type: "boolean", description: "Disable multi-query expansion (faster, narrower). Default false." },
          limit: { type: "number", description: "Max hits to return (1-50, default 8)." },
          timeout_ms: { type: "number", description: "Override the default 30s timeout (capped at 120s)." },
        },
        required: ["question"],
      },
      handler: handleQuery,
    },
    {
      name: "gbrain_search",
      description:
        "Keyword (Postgres tsvector) search over the gbrain knowledge base. Faster and more literal than " +
        "gbrain_query — use when you have exact phrases, slugs, or proper nouns to look up.",
      parameters: {
        type: "object",
        properties: {
          query: { type: "string", description: "Keyword string." },
          limit: { type: "number", description: "Max hits (1-50, default 10)." },
          timeout_ms: { type: "number", description: "Override the default 30s timeout." },
        },
        required: ["query"],
      },
      handler: handleSearch,
    },
    {
      name: "gbrain_get",
      description:
        "Fetch the full markdown content of a gbrain page by its slug. Use after gbrain_query/gbrain_search " +
        "to read the source of truth for a hit. Slug must be brain-relative (no leading '/', no '..').",
      parameters: {
        type: "object",
        properties: {
          slug: { type: "string", description: "Brain-relative page slug, e.g. notes/memo/2026-05-17." },
          timeout_ms: { type: "number", description: "Override the default 30s timeout." },
        },
        required: ["slug"],
      },
      handler: handleGet,
    },
    {
      name: "gbrain_put",
      description:
        "Write/update a gbrain page with the given markdown content. Use to PERSIST substantive new " +
        "insights, daily syntheses, or curated notes Tony will want to find later from his phone. " +
        "REFUSES writes to notes/records/private, notes/records/secrets, or any slug containing " +
        "secrets/credentials/cookies/tokens/api_keys/oauth/.env/passwords. Slug must be brain-relative.",
      parameters: {
        type: "object",
        properties: {
          slug: { type: "string", description: "Brain-relative slug, e.g. notes/knowledge/tech/ai/<topic>." },
          content: { type: "string", description: "Full markdown content. Should include frontmatter." },
          embed: { type: "boolean", description: "If true, run `gbrain embed <slug>` after the put. Default false." },
          timeout_ms: { type: "number", description: "Override the default 30s timeout (capped at 120s)." },
        },
        required: ["slug", "content"],
      },
      handler: handlePut,
    },
    {
      name: "gbrain_list",
      description:
        "List pages in gbrain by type and/or tag. Useful for diagnostics and for finding recently " +
        "updated digests (e.g. type=note, tag=calendar-digest).",
      parameters: {
        type: "object",
        properties: {
          type: { type: "string", description: "Filter by page type (e.g. note, project, person)." },
          tag: { type: "string", description: "Filter by tag." },
          limit: { type: "number", description: "Max rows (1-200, default 25)." },
          timeout_ms: { type: "number", description: "Override the default 30s timeout." },
        },
      },
      handler: handleList,
    },
  ],
});
