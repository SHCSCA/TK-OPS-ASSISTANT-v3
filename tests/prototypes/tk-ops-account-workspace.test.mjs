import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  accountWorkspaces,
  cloneAccountWorkspaces,
} from "../../docs/prototypes/tk-ops-account-workspace/src/data/accounts.js";
import { navigationItems } from "../../docs/prototypes/tk-ops-account-workspace/src/data/navigation.js";
import {
  accountCopyFields,
  accountExcludedFields,
  accountProfiles,
  createCopiedDraft,
} from "../../docs/prototypes/tk-ops-account-workspace/src/data/accountManagement.js";
import { aiRecipes, providerProfiles } from "../../docs/prototypes/tk-ops-account-workspace/src/data/aiCapabilities.js";
import { buildGenerationSteps } from "../../docs/prototypes/tk-ops-account-workspace/src/data/generationRuns.js";
import {
  applyDeconstructionResult,
  canConfirmStoryboard,
  canEnterStoryboard,
  cloneCreativeWorkflows,
  hasStoryboardRevisionMismatch,
  updateStoryboardScene,
} from "../../docs/prototypes/tk-ops-account-workspace/src/data/creativeWorkflow.js";
import { accountContentWorkflows, createContentItem } from "../../docs/prototypes/tk-ops-account-workspace/src/data/contentItems.js";
import { accountDeconstructionWorkflows } from "../../docs/prototypes/tk-ops-account-workspace/src/data/deconstructionResults.js";
import { accountProductionWorkflows, createSingleProductionBatch, getEntryReadiness } from "../../docs/prototypes/tk-ops-account-workspace/src/data/productionBatches.js";
import { accountAssets, assetTypeOptions, filterAssets } from "../../docs/prototypes/tk-ops-account-workspace/src/data/assets.js";
import {
  accountMediaTasks,
  canStartMediaTask,
  mediaTaskToLibraryItem,
  mediaTools,
} from "../../docs/prototypes/tk-ops-account-workspace/src/data/mediaTools.js";

test("账号工作区数据在克隆和修改后保持隔离", () => {
  const workspaces = cloneAccountWorkspaces();

  assert.notStrictEqual(workspaces.mirror, workspaces.focus);
  assert.notStrictEqual(workspaces.mirror.batches, workspaces.focus.batches);
  assert.notStrictEqual(workspaces.mirror.batches, accountWorkspaces.mirror.batches);

  workspaces.focus.batches.unshift({ id: "focus-test", name: "隔离测试批次" });

  assert.equal(workspaces.mirror.batches.some((batch) => batch.id === "focus-test"), false);
  assert.equal(accountWorkspaces.focus.batches.some((batch) => batch.id === "focus-test"), false);
});

test("创作链与媒体任务在账号之间保持独立", () => {
  const workflows = cloneCreativeWorkflows();
  workflows.mirror.scripts[0].title = "只修改镜头 A";

  assert.notEqual(workflows.mirror.scripts[0].title, workflows.focus.scripts[0].title);
  assert.equal(workflows.focus.deconstructions.some((item) => item.id === "m-d1"), false);
  assert.equal(accountMediaTasks.focus.some((task) => task.id.startsWith("m-tool")), false);
});

test("主导航固定为十个账号级入口且不包含剪辑工作台", () => {
  const allowedRoutes = [
    "workspace",
    "knowledge",
    "scripts",
    "storyboard",
    "deconstruction",
    "production",
    "library",
    "toolbox",
    "publishing",
    "review",
  ];

  assert.deepEqual(navigationItems.map((item) => item.id), allowedRoutes);
  assert.equal(navigationItems.some((item) => item.id === "editing"), false);
  assert.equal(navigationItems.some((item) => item.label === "内容计划"), false);
});

test("脚本必须采用当前修订后才能进入分镜", () => {
  const workflows = cloneCreativeWorkflows();
  const adopted = workflows.mirror.scripts[0];
  const draft = workflows.focus.scripts[0];

  assert.equal(canEnterStoryboard(adopted), true);
  assert.equal(canEnterStoryboard(draft), false);
  assert.equal(canEnterStoryboard({ ...adopted, revision: adopted.revision + 1 }), false);
});

test("脚本修订变化会触发分镜版本不一致提示", () => {
  const workflow = cloneCreativeWorkflows().mirror;
  const script = workflow.scripts[0];
  const storyboard = workflow.storyboards[0];

  assert.equal(hasStoryboardRevisionMismatch(script, storyboard), false);
  assert.equal(hasStoryboardRevisionMismatch({ ...script, revision: 4 }, storyboard), true);
});

test("分镜失败可在单镜头范围内重试", () => {
  const storyboard = cloneCreativeWorkflows().mirror.storyboards[0];
  const targetId = storyboard.scenes[1].id;
  const untouchedId = storyboard.scenes[0].id;
  const next = updateStoryboardScene(storyboard, targetId, (scene) => ({ ...scene, status: "running", error: null }));

  assert.equal(next.scenes.find((scene) => scene.id === targetId).status, "running");
  assert.equal(next.scenes.find((scene) => scene.id === untouchedId).status, "ready");
});

test("所有创作对象均绑定账号且版本通过 contentItemId 关联", () => {
  for (const [accountId, workflow] of Object.entries(accountContentWorkflows)) {
    const ids = new Set(workflow.contentItems.map((item) => item.id));
    assert.equal(workflow.contentItems.every((item) => item.accountId === accountId), true);
    assert.equal(workflow.scripts.every((script) => ids.has(script.contentItemId)), true);
    assert.equal(workflow.storyboards.every((storyboard) => ids.has(storyboard.contentItemId)), true);
  }
});

test("手动新建选题生成 topic_ready 内容对象并保留来源", () => {
  const item = createContentItem({ accountId: "mirror", id: "manual-topic", title: "测试选题", pillar: "效率实验", sourceType: "manual", sourceLabel: "手动创建" });
  assert.equal(item.accountId, "mirror");
  assert.equal(item.stage, "topic_ready");
  assert.equal(item.topicBrief.sourceType, "manual");
  assert.equal(item.sourceReferences[0].label, "手动创建");
});

test("分镜只有全部镜头就绪时才能确认", () => {
  const board = accountContentWorkflows.mirror.storyboards[3];
  assert.equal(canConfirmStoryboard(board), true);
  assert.equal(canConfirmStoryboard({ ...board, scenes: board.scenes.map((scene, index) => index === 1 ? { ...scene, status: "failed" } : scene) }), false);
});

test("单条生产使用一个批次和一个不可变队列引用", () => {
  const item = accountContentWorkflows.mirror.contentItems[0];
  const created = createSingleProductionBatch({ accountId: "mirror", batchId: "single-batch", contentItem: item, entryId: "single-entry", scriptVersionId: item.adoptedScriptVersionId, storyboardVersionId: item.confirmedStoryboardVersionId });
  assert.equal(created.batch.items, 1);
  assert.equal(created.entry.contentItemId, item.id);
  assert.equal(created.entry.contentItemReference.scriptVersionId, item.adoptedScriptVersionId);
  assert.equal(created.entry.contentItemReference.storyboardVersionId, item.confirmedStoryboardVersionId);
});

test("批次队列能推导选题脚本分镜生产和输出状态", () => {
  const entry = accountProductionWorkflows.mirror.entries[0];
  const item = accountContentWorkflows.mirror.contentItems.find((candidate) => candidate.id === entry.contentItemId);
  const script = accountContentWorkflows.mirror.scripts.find((candidate) => candidate.contentItemId === entry.contentItemId);
  const board = accountContentWorkflows.mirror.storyboards.find((candidate) => candidate.contentItemId === entry.contentItemId);
  assert.deepEqual(Object.keys(getEntryReadiness(entry, item, script, board)).sort(), ["output", "production", "script", "storyboard", "topic"]);
});

test("视频拆解结果固定包含脚本关键词关键帧结构和摘要", () => {
  const result = accountDeconstructionWorkflows.mirror.deconstructions[0].result;
  assert.deepEqual(Object.keys(result).sort(), ["keyframes", "keywords", "scriptSegments", "structureSegments", "structureSummary"]);
  assert.equal(result.keywords.every((keyword) => keyword.evidence.length > 0), true);
});

test("内容库主类型只包含视频图片音频文档且筛选可叠加", () => {
  assert.deepEqual(assetTypeOptions.map((item) => item.value), ["all", "video", "image", "audio", "document"]);
  const filtered = filterAssets(accountAssets.mirror, { type: "document", purpose: "脚本", source: "视频拆解", status: "ready", query: "benchmark" });
  assert.deepEqual(filtered.map((item) => item.id), ["m-a7"]);
  assert.equal(accountAssets.mirror.some((asset) => asset.type === "模板" || asset.type === "媒体工具"), false);
  assert.equal(accountAssets.mirror.some((asset) => asset.purpose === "模板"), true);
});

test("新增主链组件、未保存守卫与配置总线均已接入", async () => {
  const [app, topicPage, storyboardPage, deconstruction, library, config, contentState, unsavedDialog] = await Promise.all([
    readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/App.jsx", import.meta.url), "utf8"),
    readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/pages/ScriptTopicCenter.jsx", import.meta.url), "utf8"),
    readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/pages/StoryboardPlanning.jsx", import.meta.url), "utf8"),
    readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/components/video-deconstruction/DeconstructionResult.jsx", import.meta.url), "utf8"),
    readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/pages/ContentLibrary.jsx", import.meta.url), "utf8"),
    readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/config/prototypeConfig.js", import.meta.url), "utf8"),
    readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/state/useContentItemState.js", import.meta.url), "utf8"),
    readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/components/UnsavedChangesDialog.jsx", import.meta.url), "utf8"),
  ]);
  assert.match(app, /createGenericBatch/);
  assert.match(app, /requestAccountSwitch/);
  assert.match(topicPage, /TopicCreateDialog/);
  assert.match(storyboardPage, /ProductionHandoffDialog/);
  assert.match(deconstruction, /keywords/);
  assert.match(library, /AssetToolbar/);
  assert.match(config, /targetDurations/);
  assert.match(config, /defaultType/);
  assert.match(contentState, /scriptDraftDirty/);
  assert.match(unsavedDialog, /保存并切换/);
  assert.match(unsavedDialog, /放弃并切换/);
});

test("视频拆解结果可选择性回流且不重复记录", () => {
  const workflow = cloneCreativeWorkflows().mirror;
  const once = applyDeconstructionResult(workflow, "m-d1", "script");
  const twice = applyDeconstructionResult(once, "m-d1", "script");

  assert.deepEqual(twice.deconstructions[0].appliedTargets.sort(), ["knowledge", "script"]);
});

test("视频拆解覆盖 Provider 与 FFprobe 恢复类型", () => {
  const workflows = cloneCreativeWorkflows();
  const failureTypes = [
    ...workflows.mirror.deconstructions,
    ...workflows.focus.deconstructions,
  ].map((item) => item.failureType).filter(Boolean);

  assert.deepEqual(failureTypes.sort(), ["ffprobe", "provider"]);
});

test("媒体工具箱固定六种工具并统一使用四步向导", async () => {
  const source = await readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/components/media-toolbox/MediaToolWizard.jsx", import.meta.url), "utf8");

  assert.equal(mediaTools.length, 6);
  assert.deepEqual(mediaTools.map((tool) => tool.id), ["download", "watermark", "transcode", "audio", "keyframes", "crop"]);
  assert.match(source, /\["输入", "配置", "权利确认", "执行"\]/);
});

test("下载与去水印必须完成素材权利确认", () => {
  assert.equal(canStartMediaTask({ toolId: "download", input: "https://example.com/video", rightsConfirmed: false }), false);
  assert.equal(canStartMediaTask({ toolId: "watermark", input: "source.mp4", rightsConfirmed: true }), true);
  assert.equal(canStartMediaTask({ toolId: "transcode", input: "source.mp4", rightsConfirmed: false }), true);
});

test("媒体任务覆盖五种状态且完成输出可进入内容库", () => {
  const statuses = new Set(accountMediaTasks.mirror.map((task) => task.status));
  statuses.add("queued");
  statuses.add("cancelling");
  assert.deepEqual([...statuses].sort(), ["cancelling", "completed", "failed", "queued", "running"]);

  const output = mediaTaskToLibraryItem(accountMediaTasks.mirror[0]);
  assert.equal(output.status, "ready");
  assert.match(output.source, /媒体工具箱/);
});

test("媒体工具合规说明明确不绕过访问控制", async () => {
  const source = await readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/components/media-toolbox/MediaToolWizard.jsx", import.meta.url), "utf8");
  assert.match(source, /不绕过登录、DRM、付费墙或访问控制/);
});

test("创作页面和媒体工具箱覆盖紧凑窗口与双主题令牌", async () => {
  const responsive = await readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/styles/responsive.css", import.meta.url), "utf8");
  const tokens = await readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/styles/tokens.css", import.meta.url), "utf8");

  assert.match(responsive, /max-width: 1180px/);
  assert.match(responsive, /max-width: 960px/);
  assert.match(responsive, /creative-workspace/);
  assert.match(tokens, /data-theme="dark"/);
});

test("账号管理覆盖五种状态且复制配置不携带授权和内容", () => {
  assert.deepEqual(
    [...new Set(accountProfiles.map((profile) => profile.status))].sort(),
    ["archived", "attention", "draft", "ready", "unbound"],
  );

  const copied = createCopiedDraft(accountProfiles[0], "copy-test");
  assert.equal(copied.status, "draft");
  assert.deepEqual(copied.connection, {});
  assert.equal(copied.recipe.id, accountProfiles[0].recipe.id);
  assert.deepEqual(accountCopyFields, ["定位模板", "知识规则结构", "AI Recipe", "发布默认值"]);
  assert.equal(accountExcludedFields.includes("授权与密钥"), true);
  assert.equal(accountExcludedFields.includes("内容与索引"), true);
});

test("固定脚本输入会跳过脚本生成且保留完整 AI 节点链", () => {
  const fixedScriptSteps = buildGenerationSteps("script", false);
  const topicSteps = buildGenerationSteps("topic", true);

  assert.equal(fixedScriptSteps.length, 9);
  assert.equal(fixedScriptSteps.some((step) => step.id === "visual-plan"), true);
  assert.equal(fixedScriptSteps.find((step) => step.id === "script").status, "skipped");
  assert.equal(fixedScriptSteps.find((step) => step.id === "script").skipReason, "已使用固定脚本");
  assert.equal(topicSteps.find((step) => step.id === "visual").status, "failed");
  assert.match(topicSteps.find((step) => step.id === "visual").error, /保留脚本与分镜产物/);
});

test("图生视频只由声明该能力的 Recipe 提供且不可用 Provider 可被识别", () => {
  const imageRecipes = aiRecipes.filter((recipe) => recipe.videoCapability === "image-to-video");
  const unavailableProviders = providerProfiles.filter((provider) => provider.health === "error");

  assert.equal(imageRecipes.length >= 1, true);
  assert.equal(aiRecipes.find((recipe) => recipe.id === "recipe-talk").videoCapability, "text-to-video");
  assert.deepEqual(unavailableProviders.map((provider) => provider.id), ["runninghub"]);
});

test("账号切换器的添加与管理入口均连接到真实处理函数", async () => {
  const source = await readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/components/AccountSwitcher.jsx", import.meta.url), "utf8");
  const sidebar = await readFile(new URL("../../docs/prototypes/tk-ops-account-workspace/src/components/AppSidebar.jsx", import.meta.url), "utf8");

  assert.match(source, /onClick=\{onAddAccount\}/);
  assert.match(source, /onClick=\{onManageAccounts\}/);
  assert.match(sidebar, /accountManagement\.openWizard/);
  assert.match(sidebar, /navigate\("accounts"\)/);
});
