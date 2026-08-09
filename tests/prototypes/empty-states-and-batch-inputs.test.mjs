import assert from "node:assert/strict";
import test from "node:test";

import { prototypeConfig } from "../../docs/prototypes/tk-ops-account-workspace/src/config/prototypeConfig.js";
import { emptyStateDefinitions } from "../../docs/prototypes/tk-ops-account-workspace/src/data/emptyStateDefinitions.js";
import { splitFixedScript, validateBatchSource } from "../../docs/prototypes/tk-ops-account-workspace/src/components/batch-wizard/batchWizardHelpers.js";
import { resolvePageEmptyState } from "../../docs/prototypes/tk-ops-account-workspace/src/utils/resolvePageEmptyState.js";

test("页面空态由数据场景和页面语义共同决定", () => {
  assert.equal(resolvePageEmptyState("scripts", "seeded", true), null);
  assert.equal(resolvePageEmptyState("scripts", "empty", true).actionId, "new-topic");
  assert.equal(resolvePageEmptyState("library", "seeded", false), emptyStateDefinitions.library);
  assert.equal(Object.keys(emptyStateDefinitions).length, 10);
});

test("固定脚本支持段落行与句子三种拆分方式", () => {
  const script = "第一条内容。\n第二条内容！\n\n第三条内容？";
  assert.equal(splitFixedScript(script, "paragraph").length, 2);
  assert.equal(splitFixedScript(script, "line").length, 3);
  assert.equal(splitFixedScript(script, "sentence").length, 3);
  assert.equal(prototypeConfig.production.scriptSplitModes.length, 3);
});

test("固定脚本和素材输入必须满足各自的可执行条件", () => {
  assert.equal(validateBatchSource({ mode: "script", fixedScript: "", splitMode: "paragraph", assetIds: [] }, []), "请粘贴固定脚本");
  assert.equal(validateBatchSource({ mode: "assets", fixedScript: "", splitMode: "paragraph", assetIds: [] }, [{ id: "a1" }]), "请选择至少一项账号素材");
  assert.equal(validateBatchSource({ mode: "assets", fixedScript: "", splitMode: "paragraph", assetIds: ["a1"] }, [{ id: "a1" }]), "");
});
