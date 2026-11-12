import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

// Exercise the actual client without introducing a frontend test framework.
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

const calls = [
  ["search", (api) => api.searchArticles({ query: "test" })],
  ["clusters", (api) => api.getClusters()],
  ["cluster detail page 2", (api) => api.getClusterDetail(999, 2, 10)],
  ["chat", (api) => api.chatQuery("test")],
];

for (const [name, call] of calls) {
  test(`${name} propagates network errors without synthetic results`, async () => {
    await assert.rejects(call(client(async () => { throw new Error("network unavailable"); })), /network unavailable/);
  });
  for (const status of [404, 503]) {
    test(`${name} reports HTTP ${status} detail without synthetic results`, async () => {
      const api = client(async () => new Response(JSON.stringify({ detail: "Service unavailable" }), { status }));
      await assert.rejects(call(api), new RegExp(`\\(${status}\\): Service unavailable`));
    });
  }
}

test("successful empty search and clusters stay empty", async () => {
  const api = client(async () => new Response("[]", { status: 200 }));
  assert.equal((await api.searchArticles({ query: "test" })).length, 0);
  assert.equal((await api.getClusters()).length, 0);
});

test("successful wrapped responses stay intact, including empty arrays", async () => {
  const api = client(async () => new Response('{"results":[],"clusters":[]}', { status: 200 }));
  assert.equal((await api.searchArticles({ query: "test" })).length, 0);
  assert.equal((await api.getClusters()).length, 0);
});

test("HTTP errors without JSON still report status", async () => {
  const api = client(async () => new Response("Unavailable", { status: 503, statusText: "Service Unavailable" }));
  await assert.rejects(api.getClusters(), /503.*Service Unavailable/);
});
