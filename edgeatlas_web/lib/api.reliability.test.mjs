import assert from "node:assert/strict";
import { test } from "node:test";
import { readFileSync } from "node:fs";
import ts from "typescript";

const source = readFileSync(new URL("./api.ts", import.meta.url), "utf8");
const js = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;

const exports = {};
new Function("exports", "require", "process", js)(
  exports,
  () => { throw Error("Unexpected import"); },
  { env: { SIGNALATLAS_API_URL: "http://127.0.0.1:8011" } },
);

const originalFetch = globalThis.fetch;

async function check(status, body, expected) {
  globalThis.fetch = async () => ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
  const result = await exports.getSignalStatus();
  assert.equal(result.reliability, expected);
  assert.equal(result.data !== null, expected === "HEALTHY" || expected === "PENDING");
}

test("SignalAtlas reliability response mapping", async () => {
  try {
    for (const state of ["HEALTHY", "PENDING"]) {
      await check(200, { measurement: { reliability: { state } } }, state);
    }
    await check(503, {
      detail: { reason: "measurement_reliability_degraded" },
    }, "DEGRADED");
    await check(503, { detail: "measurement_health_stale" }, "UNAVAILABLE");
    await check(200, { measurement: { reliability: { state: "INVALID" } } }, "UNAVAILABLE");
    await check(200, [], "UNAVAILABLE");
    globalThis.fetch = async () => { throw Error("Connection failed"); };
    assert.equal((await exports.getSignalStatus()).reliability, "UNAVAILABLE");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
