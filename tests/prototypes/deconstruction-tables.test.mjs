import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { accountDeconstructionWorkflows } from "../../docs/prototypes/tk-ops-account-workspace/src/data/deconstructionResults.js";

test("拆解四类结果具有稳定的表格语义字段", () => {
  const result = accountDeconstructionWorkflows.mirror.deconstructions[0].result;
  assert.deepEqual(Object.keys(result.scriptSegments[0]).sort(), ["confidence", "end", "id", "role", "start", "text"]);
  assert.deepEqual(Object.keys(result.keywords[0]).sort(), ["evidence", "group", "hits", "id", "label", "weight"]);
  assert.equal(result.keyframes.every((frame) => "reuse" in frame && "note" in frame), true);
  assert.equal(result.structureSegments.every((segment) => "copy" in segment && "evidenceKeywords" in segment), true);
  assert.equal(result.structureSummary.tags.length >= 3, true);
});

test("拆解结果使用表格组件并提供证据时间交互", async () => {
  const [table, keyword, structure] = await Promise.all([
    readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/components/video-deconstruction/ResultDataTable.jsx", import.meta.url), "utf8"),
    readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/components/video-deconstruction/KeywordResult.jsx", import.meta.url), "utf8"),
    readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/components/video-deconstruction/StructureResult.jsx", import.meta.url), "utf8"),
  ]);
  assert.match(table, /<table/);
  assert.match(keyword, /onEvidence/);
  assert.match(structure, /structure-summary/);
});
