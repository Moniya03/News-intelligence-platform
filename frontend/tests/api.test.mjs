import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = fs.readFileSync(fileURLToPath(new URL("../src/lib/api.ts", import.meta.url)), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;

function client(fetch) {
  const context = {
    exports: {}, process: { env: {} }, fetch, AbortController, setTimeout, clearTimeout,
  };
  vm.runInNewContext(compiled, context);
  return context.exports;
}

test("search preserves backend response metadata and sends the selected request", async () => {
  let request;
  const response = {
    results: [{ article_id: "a", score: 0.42, snapshot_id: "snap" }],
    metadata: { snapshot_id: "snap", requested_mode: "bm25", executed_mode: "bm25", reranker_status: "disabled", elapsed_ms: 12 },
  };
  const api = client(async (url, options) => {
    request = { url, options };
    return new Response(JSON.stringify(response), { status: 200 });
  });
  assert.deepEqual(await api.searchArticles({ query: "news", mode: "bm25", lang_filter: ["mr"] }), response);
  assert.match(request.url, /\/api\/search$/);
  assert.deepEqual(JSON.parse(request.options.body), { query: "news", mode: "bm25", lang_filter: ["mr"] });
});

test("topics, topic detail, corpus, and summary preserve their backend envelopes", async () => {
  const responses = [
    { snapshot_id: "snap", clusters: [], topic_count: 0 },
    { snapshot_id: "snap", run_id: "run", settings_hash: "hash", articles: [], total: 0, cluster: { id: 1 } },
    { snapshot_id: "snap", article_count: 0, language_counts: { mr: 0 } },
    { status: "unavailable", summary: null, citations: [], snapshot_id: "snap", reason: "provider_access_unverified" },
  ];
  const urls = [];
  const api = client(async (url) => {
    urls.push(url);
    return new Response(JSON.stringify(responses.shift()), { status: 200 });
  });
  assert.equal((await api.getClusters()).snapshot_id, "snap");
  assert.equal((await api.getClusterDetail(7, 2, 10)).total, 0);
  assert.equal((await api.corpusSummary()).article_count, 0);
  assert.equal((await api.summarizeSearch({ query: "news", article_ids: ["id"], snapshot_id: "snap" })).status, "unavailable");
  assert.match(urls[0], /\/api\/clusters$/);
  assert.match(urls[1], /\/api\/clusters\/7\?page=2&limit=10$/);
  assert.match(urls[2], /\/api\/corpus$/);
  assert.match(urls[3], /\/api\/search\/summary$/);
});

for (const [name, call] of [
  ["search", (api) => api.searchArticles({ query: "test" })],
  ["topics", (api) => api.getClusters()],
  ["topic detail", (api) => api.getClusterDetail(999)],
  ["corpus", (api) => api.corpusSummary()],
  ["summary", (api) => api.summarizeSearch({ query: "test", article_ids: ["id"], snapshot_id: "snap" })],
]) {
  test(`${name} propagates network errors`, async () => {
    await assert.rejects(call(client(async () => { throw new Error("network unavailable"); })), /network unavailable/);
  });
  test(`${name} reports HTTP error detail`, async () => {
    const api = client(async () => new Response(JSON.stringify({ detail: "Service unavailable" }), { status: 503 }));
    await assert.rejects(call(api), /503.*Service unavailable/);
  });
}

test("successful empty responses stay empty instead of becoming errors", async () => {
  const api = client(async () => new Response(JSON.stringify({
    results: [], metadata: { snapshot_id: "snap", requested_mode: "hybrid", executed_mode: "hybrid", reranker_status: "disabled", elapsed_ms: 0 },
  }), { status: 200 }));
  const result = await api.searchArticles({ query: "test" });
  assert.equal(result.results.length, 0);
  assert.equal(result.metadata.snapshot_id, "snap");
});


test("summary rejects a mismatched snapshot without replacing search results", async () => {
  const api = client(async () => new Response(JSON.stringify({
    status: "available", summary: "Stale summary", citations: [], snapshot_id: "other", reason: null,
  }), { status: 200 }));
  await assert.rejects(api.summarizeSearch({ query: "news", article_ids: ["id"], snapshot_id: "snap" }), /snapshot changed/);
});
