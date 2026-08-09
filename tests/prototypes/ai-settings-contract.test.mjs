import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { capabilityRoutes } from "../../docs/prototypes/tk-ops-account-workspace/src/data/ai/capabilityRoutes.js";
import { modelProfiles } from "../../docs/prototypes/tk-ops-account-workspace/src/data/ai/modelProfiles.js";
import { promptProfiles } from "../../docs/prototypes/tk-ops-account-workspace/src/data/ai/promptProfiles.js";
import { providerProfiles } from "../../docs/prototypes/tk-ops-account-workspace/src/data/ai/providerProfiles.js";
import { getRouteStatus } from "../../docs/prototypes/tk-ops-account-workspace/src/state/ai-settings/useAIConfigurationState.js";

test("Provider 模型 Prompt 与能力路由使用独立数据模型", () => {
  assert.equal(providerProfiles.every((provider) => Array.isArray(provider.modelIds)), true);
  assert.equal(modelProfiles.every((model) => Array.isArray(model.declaredAbilities) && Array.isArray(model.adapterAbilities)), true);
  assert.equal(promptProfiles.every((prompt) => prompt.outputSchema && Array.isArray(prompt.variables)), true);
  assert.equal(capabilityRoutes.length, 12);
});

test("能力路由会拒绝缺模型、未验证模型与适配器能力不匹配", () => {
  const ready = capabilityRoutes.find((route) => route.id === "image-to-video");
  const missing = capabilityRoutes.find((route) => route.id === "text-to-video");
  assert.equal(getRouteStatus(ready, modelProfiles, promptProfiles).ready, true);
  assert.equal(getRouteStatus(missing, modelProfiles, promptProfiles).reason, "缺少主模型");
  assert.equal(getRouteStatus({ ...ready, id: "text-to-video" }, modelProfiles, promptProfiles).reason, "适配器能力不匹配");
});

test("添加 Provider 与 Prompt 保存均为真实交互入口", async () => {
  const [center, wizard, editor] = await Promise.all([
    readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/components/ai-capabilities/AICapabilitiesCenter.jsx", import.meta.url), "utf8"),
    readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/components/ai-capabilities/ProviderWizard.jsx", import.meta.url), "utf8"),
    readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/components/ai-capabilities/PromptProfileEditor.jsx", import.meta.url), "utf8"),
  ]);
  assert.match(center, /openProviderWizard/);
  assert.match(wizard, /discoverDemoModels/);
  assert.match(wizard, /onSave/);
  assert.match(editor, /保存新版本/);
});
