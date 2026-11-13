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

test("topics, topic detail, corpus, and Ask preserve their backend envelopes", async () => {
  const responses = [
    { snapshot_id: "snap", clusters: [], topic_count: 0 },
    { snapshot_id: "snap", run_id: "run", settings_hash: "hash", articles: [], total: 0, cluster: { id: 1 } },
    { snapshot_id: "snap", article_count: 0, language_counts: { mr: 0 } },
    { status: "generation_unavailable", answer_segments: [], gap: null, citations: [], snapshot_id: "snap", reason: "provider_unavailable" },
  ];
  const urls = [];
  const api = client(async (url) => {
    urls.push(url);
    return new Response(JSON.stringify(responses.shift()), { status: 200 });
  });
  assert.equal((await api.getClusters()).snapshot_id, "snap");
  assert.equal((await api.getClusterDetail(7, 2, 10)).total, 0);
  assert.equal((await api.corpusSummary()).article_count, 0);
  assert.equal((await api.askQuestion({ question: "news" })).status, "generation_unavailable");
  assert.match(urls[0], /\/api\/clusters$/);
  assert.match(urls[1], /\/api\/clusters\/7\?page=2&limit=10$/);
  assert.match(urls[2], /\/api\/corpus$/);
  assert.match(urls[3], /\/api\/ask$/);
});

for (const [name, call] of [
  ["search", (api) => api.searchArticles({ query: "test" })],
  ["topics", (api) => api.getClusters()],
  ["topic detail", (api) => api.getClusterDetail(999)],
  ["corpus", (api) => api.corpusSummary()],
  ["Ask", (api) => api.askQuestion({ question: "test" })],
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


test("Ask sends one standalone question and preserves claim citation links and evidence", async () => {
  let request;
  const response = {
    status: "answered", answer_segments: [{ text: "Supported claim", citation_ids: ["C1"] }], gap: "An unanswered part",
    citations: [{ citation_id: "C1", chunk_id: "chunk", article_id: "article", passage: "<script>untrusted text</script>", title: "A title", url: "https://example.com/article", source: "Publisher", language: "hi", published_at: null }],
    snapshot_id: "snap",
  };
  const api = client(async (url, options) => {
    request = { url, options };
    return new Response(JSON.stringify(response), { status: 200 });
  });
  assert.deepEqual(await api.askQuestion({ question: "क्या हुआ?" }), response);
  assert.deepEqual(JSON.parse(request.options.body), { question: "क्या हुआ?" });
  assert.match(request.url, /\/api\/ask$/);
});
