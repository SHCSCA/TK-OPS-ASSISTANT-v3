import {
  expect,
  test,
  type Locator,
  type Page
} from "@playwright/test";

import type {
  AIExecutionDetailDto,
  AIExecutionEvidenceDto,
  AIExecutionPageDto
} from "../../src/types/runtime/ai-executions";
import { prepareP0HRuntimeChain } from "./support/p0-h-runtime-chain";
import { callRuntime } from "./support/runtime-api";
import { readE2eRuntimeState } from "./support/runtime-state";

test.describe.configure({ mode: "serial" });

test("真实 Runtime 与受控 Provider 完成 P0-H 纵向执行链", async ({
  page,
  request
}) => {
  test.setTimeout(180_000);
  await ensureWorkspaceReady(page);
  const chain = await prepareP0HRuntimeChain(request);
  const state = readE2eRuntimeState();

  await page.reload();
  await selectAccount(page, chain.accountName);
  await openAccountManagement(page);
  await page.locator(`tr[data-account-id="${chain.accountId}"]`).click();
  await expect(page.locator(
    `.account-detail[data-account-id="${chain.accountId}"]`
  )).toBeVisible();
  await page.getByRole("button", { name: "AI 创作档案" }).click();

  const recipe = page.locator(
    `.recipe-panel[data-account-id="${chain.accountId}"]`
  );
  await expect(recipe).toContainText("P0-H 真实执行 Recipe");
  const launcher = recipe.locator(".ai-execution-workspace");
  await expect(launcher.getByRole("heading", { name: "真实调用验证" }))
    .toBeVisible();
  await launcher.getByLabel("验证主题").fill("如何建立稳定的短视频选题流程");
  await expect(launcher.getByLabel("知识快照"))
    .toHaveValue(chain.knowledgeSnapshotId);

  await launcher.getByRole("button", { name: "预检", exact: true }).click();
  await expect(launcher).toContainText("预检通过，已冻结候选、知识与成本摘要。");
  const preflight = launcher.locator(".ai-execution-preflight");
  await expect(preflight).toContainText("候选 1");
  await expect(preflight).toContainText("预算");
  await expect(preflight).toContainText("快照");

  const accepted = page.waitForResponse((response) =>
    response.url().endsWith(`/api/v1/accounts/${chain.accountId}/ai-executions`)
    && response.request().method() === "POST"
  );
  await launcher.getByRole("button", { name: "运行真实调用" }).click();
  expect((await accepted).ok()).toBe(true);
  const detailPanel = launcher.getByRole("complementary", {
    name: "AI 执行详情"
  });
  await expect(detailPanel.getByRole("heading", { name: "已完成" }))
    .toBeVisible({ timeout: 60_000 });
  await expect(detailPanel).toContainText("用量");
  await expect(detailPanel).not.toContainText("费用待确认");
  await detailPanel.getByRole("button", { name: "查看正文" }).click();
  await expect(detailPanel.locator("pre")).toContainText(
    "先给结论，再用三个步骤说明稳定选题流程。"
  );
  await expect(page.locator("body")).not.toContainText(state.providerCredential);

  const executions = await callRuntime<AIExecutionPageDto>(
    request,
    `/api/v1/accounts/${chain.accountId}/ai-executions?limit=20`
  );
  expect(executions.data.items).toHaveLength(1);
  const executionId = executions.data.items[0]!.id;
  const detail = await callRuntime<AIExecutionDetailDto>(
    request,
    `/api/v1/accounts/${chain.accountId}/ai-executions/${executionId}`
  );
  expect(detail.data).toMatchObject({
    accountId: chain.accountId,
    completionKind: "succeeded",
    costStatus: "estimated",
    outputCount: 1,
    status: "completed"
  });
  expect(detail.data.snapshot).toMatchObject({
    knowledge: { snapshotId: chain.knowledgeSnapshotId },
    recipe: { id: chain.recipeVersionId }
  });
  expect(detail.data.candidates[0]).toMatchObject({
    modelProfileId: chain.modelProfileId,
    providerProfileId: chain.providerProfileId
  });
  expect(detail.data.usage[0]).toMatchObject({
    costSource: "estimated",
    inputUnits: 18,
    outputUnits: 12,
    pricingRevision: 1,
    totalUnits: 30
  });

  const evidence = await callRuntime<AIExecutionEvidenceDto>(
    request,
    `/api/v1/accounts/${chain.accountId}/ai-executions/${executionId}/evidence`
  );
  expect(evidence.data).toMatchObject({
    accountId: chain.accountId,
    capabilityKey: "script_generation",
    executionId,
    finalStatus: "succeeded",
    provider: {
      adapterType: "openai_compatible",
      validationStage: "real_small_call",
      validationStatus: "verified"
    },
    snapshotHash: detail.data.snapshotHash
  });
  expect(evidence.data.usageReported).toBe(true);
  expect(evidence.data.responseIdHash).toMatch(/^[a-f0-9]{64}$/);
  expect(evidence.data.outputs[0]?.contentHash)
    .toBe(detail.data.outputs[0]?.contentHash);
  expect(JSON.stringify(evidence.data)).not.toContain(state.providerCredential);
  expect(JSON.stringify(evidence.data)).not.toContain(
    "先给结论，再用三个步骤说明稳定选题流程。"
  );

  const isolated = await request.get(
    `${state.runtimeBaseUrl}/api/v1/accounts/${chain.isolationAccountId}`
    + `/ai-executions/${executionId}`,
    { headers: { Authorization: `Bearer ${state.sessionToken}` } }
  );
  expect(isolated.status()).toBe(404);
  expect(await isolated.json()).toMatchObject({
    error_code: "AI_EXECUTION_NOT_FOUND",
    ok: false
  });

  const providerEvidenceResponse = await request.get(
    `${state.providerBaseUrl}/__e2e__/evidence`
  );
  expect(providerEvidenceResponse.ok()).toBe(true);
  const providerEvidence = await providerEvidenceResponse.json() as {
    authorizedRequests: number;
    chatCompletionRequests: number;
    evidenceKind: string;
    modelsRequests: number;
    providerEvidenceKind: string;
    reportedUsageResponses: number;
  };
  expect(providerEvidence).toMatchObject({
    evidenceKind: "p0h_controlled_contract",
    providerEvidenceKind: "controlled_contract"
  });
  expect(providerEvidence.modelsRequests).toBeGreaterThanOrEqual(2);
  expect(providerEvidence.chatCompletionRequests).toBeGreaterThanOrEqual(2);
  expect(providerEvidence.reportedUsageResponses).toBeGreaterThanOrEqual(2);
  expect(providerEvidence.authorizedRequests).toBeGreaterThanOrEqual(4);
  expect(JSON.stringify(providerEvidence)).not.toContain(state.providerCredential);
});

async function ensureWorkspaceReady(page: Page): Promise<void> {
  const state = readE2eRuntimeState();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/workspace");
  const licenseInput = page.getByLabel("许可证密钥");
  if (await waitUntilVisible(licenseInput)) {
    await licenseInput.fill(state.licenseKey);
    await page.getByRole("button", { name: "激活并继续" }).click();
  }
  const directoryStep = page.getByRole("heading", {
    name: "初始化本地目录"
  });
  if (await waitUntilVisible(directoryStep)) {
    await page.getByRole("button", { name: "初始化目录" }).click();
  }
  const selfCheck = page.getByRole("heading", { name: "运行环境自检" });
  if (await waitUntilVisible(selfCheck)) {
    await page.getByRole("button", { name: "开始自检" }).click();
  }
  const ready = page.getByRole("heading", { name: "本机环境已就绪" });
  if (await waitUntilVisible(ready)) {
    await page.getByRole("button", { name: "进入工作区" }).click();
  }
  await expect(page).toHaveURL(/\/workspace$/);
  await expect(page.locator(".account-switcher__trigger")).toBeVisible();
}

async function selectAccount(page: Page, name: string): Promise<void> {
  const trigger = page.locator(".account-switcher__trigger");
  const menu = page.getByRole("dialog", { name: "切换账号" });
  if ((await trigger.innerText()).includes(name)) return;

  for (let attempt = 0; attempt < 3; attempt += 1) {
    await waitForAccountShellIdle(page);
    if (!await openAccountMenuAfterRefresh(trigger, menu)) continue;
    const option = menu.locator(".account-switcher__option")
      .filter({ hasText: name });
    try {
      await expect(option).toBeEnabled({ timeout: 2_000 });
      await option.click({ timeout: 2_000 });
    } catch (error) {
      if ((await trigger.innerText()).includes(name)) break;
      if (attempt === 2) throw error;
      continue;
    }
    await expect(trigger).toContainText(name, { timeout: 30_000 });
    break;
  }

  await expect(trigger).toContainText(name);
  await waitForAccountShellIdle(page);
}

async function openAccountManagement(page: Page): Promise<void> {
  const trigger = page.locator(".account-switcher__trigger");
  const menu = page.getByRole("dialog", { name: "切换账号" });

  for (let attempt = 0; attempt < 3; attempt += 1) {
    await waitForAccountShellIdle(page);
    if (!await openAccountMenuAfterRefresh(trigger, menu)) continue;
    try {
      await menu.getByRole("button", { name: "管理账号" })
        .click({ timeout: 2_000 });
      await expect(page).toHaveURL(/\/settings\/accounts$/);
      return;
    } catch (error) {
      if (/\/settings\/accounts$/.test(new URL(page.url()).pathname)) return;
      if (attempt === 2) throw error;
    }
  }

  throw new Error("后台刷新结束后仍无法打开账号管理。");
}

async function openAccountMenuAfterRefresh(
  trigger: Locator,
  menu: Locator
): Promise<boolean> {
  if (await menu.isVisible()) return true;
  try {
    await trigger.click({ timeout: 2_000 });
    await menu.waitFor({ state: "visible", timeout: 1_000 });
    return true;
  } catch {
    if (await menu.isVisible()) return true;
    await expect(trigger).toBeEnabled();
    return false;
  }
}

async function waitForAccountShellIdle(page: Page): Promise<void> {
  const trigger = page.locator(".account-switcher__trigger");
  await expect(trigger).toBeVisible();
  await expect(trigger).toBeEnabled({ timeout: 30_000 });
  await expect(page.locator(".account-workspace-switch-mask"))
    .toBeHidden({ timeout: 30_000 });
}

async function waitUntilVisible(locator: Locator): Promise<boolean> {
  return locator.waitFor({ state: "visible", timeout: 15_000 })
    .then(() => true)
    .catch(() => false);
}
