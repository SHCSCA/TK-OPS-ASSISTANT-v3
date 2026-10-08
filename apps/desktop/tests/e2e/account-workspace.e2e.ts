import {
  expect,
  test,
  type Locator,
  type Page
} from "@playwright/test";

import {
  findAccount,
  getAccount,
  prepareP0MainChain
} from "./support/p0-main-chain";
import {
  callRuntime,
  waitForRuntimeTask
} from "./support/runtime-api";
import { readE2eRuntimeState } from "./support/runtime-state";

test.describe.configure({ mode: "serial" });

test.beforeEach(async ({ page, request }) => {
  await ensureWorkspaceReady(page);
  await ensureAccountFixtures(request);
  await page.reload();
  await waitForAccountShellIdle(page);
});

test("账号切换后详情与工作区内容只显示当前账号", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/workspace");

  await selectAccount(page, "账号 Alpha");
  await expect(page.getByRole("heading", { name: "账号 Alpha" }))
    .toBeVisible();
  await page.getByRole("button", { name: "查看当前账号详情" }).click();
  const detail = page.getByTestId("account-context-detail");
  await expect(detail).toContainText("@alpha_creator");
  await expect(detail).not.toContainText("账号 Beta");
  await detail.getByRole("button", { name: "关闭账号详情" }).last().click();

  await selectAccount(page, "账号 Beta");
  await expect(page.getByRole("heading", { name: "账号 Beta" }))
    .toBeVisible();
  await expect(page.locator(".account-switcher__trigger"))
    .toContainText("@beta_creator");
  await expect(page.getByText("@alpha_creator")).toHaveCount(0);
});

test("定位版本可查看、派生修改并完成三种未保存决策", async ({
  page,
  request
}) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/workspace");
  await selectAccount(page, "账号 Alpha");
  const alpha = await findAccount(request, "alpha_creator");

  await page.getByRole("link", { name: "定位与知识" }).click();
  await expect(page).toHaveURL(/\/strategy-knowledge$/);
  await page.getByRole("button", { name: "新建定位" }).click();
  await fillPositioningEditor(page, "准备出海的独立开发者");
  await page.getByRole("button", { name: "保存草稿版本" }).click();

  const detailPanel = page.getByTestId("positioning-detail-panel");
  await expect(detailPanel).toBeVisible();
  await expect(detailPanel).toContainText("v1 详情");
  await expect(detailPanel).toContainText("准备出海的独立开发者");
  await expect(detailPanel).toContainText("未经验证的收益承诺");
  await detailPanel.getByRole("button", { name: "基于此版本修改" }).click();
  await page.getByLabel("目标受众").fill("准备出海的独立开发者与小团队");
  await page.getByRole("button", { name: "保存为新版本" }).click();

  try {
    await detailPanel.waitFor({ state: "visible", timeout: 5_000 });
  } catch {
    await expect(page.locator(".positioning-detail-backdrop")).toBeHidden();
    await page.getByRole("button", {
      name: "查看定位版本 v2 详情"
    }).click();
  }
  await expect(detailPanel).toContainText("v2 详情");
  await expect(detailPanel).toContainText("独立开发者与小团队");
  const v1 = await callRuntime<{
    audience: { description: string };
    contentHash: string;
    version: number;
  }>(request, `/api/v1/accounts/${alpha.id}/positioning/versions/1`);
  const v2 = await callRuntime<{
    audience: { description: string };
    contentHash: string;
    status: string;
    version: number;
  }>(request, `/api/v1/accounts/${alpha.id}/positioning/versions/2`);
  expect(v1.data.audience.description).toBe("准备出海的独立开发者");
  expect(v2.data).toMatchObject({
    audience: { description: "准备出海的独立开发者与小团队" },
    status: "draft",
    version: 2
  });
  expect(v2.data.contentHash).not.toBe(v1.data.contentHash);

  await detailPanel.getByRole("button", { name: "设为使用中" }).click();
  await expect(detailPanel).toContainText("使用中");
  await detailPanel.getByRole("button", { name: "基于此版本修改" }).click();
  await page.getByLabel("目标受众").fill("取消决策保留的受众草稿");
  await beginDirtyAccountSwitch(page, "账号 Beta");
  await page.getByRole("dialog", { name: "仍有未保存内容" })
    .getByRole("button", { name: "取消" }).click();
  const switchTrigger = page.locator(".account-switcher__trigger");
  await expect(page.getByRole("dialog", { name: "仍有未保存内容" }))
    .toBeHidden();
  await expect(switchTrigger).toBeEnabled();
  await expect(switchTrigger)
    .toContainText("账号 Alpha");
  await expect(page.getByLabel("目标受众"))
    .toHaveValue("取消决策保留的受众草稿");

  await beginDirtyAccountSwitch(page, "账号 Beta");
  await page.getByRole("dialog", { name: "仍有未保存内容" })
    .getByRole("button", { name: "放弃并继续" }).click();
  await expect(page.locator(".account-switcher__trigger"))
    .toContainText("账号 Beta");

  await selectAccount(page, "账号 Alpha");
  await page.getByRole("link", { name: "定位与知识" }).click();
  await expect(page).toHaveURL(/\/strategy-knowledge$/);
  await page.getByRole("button", { name: "编辑定位" }).click();
  await page.getByLabel("目标受众").fill("保存决策生成的新受众版本");
  await beginDirtyAccountSwitch(page, "账号 Beta");
  await page.getByRole("dialog", { name: "仍有未保存内容" })
    .getByRole("button", { name: "保存并继续" }).click();
  await expect(page.locator(".account-switcher__trigger"))
    .toContainText("账号 Beta");
  const v3 = await callRuntime<{
    audience: { description: string };
    status: string;
    version: number;
  }>(request, `/api/v1/accounts/${alpha.id}/positioning/versions/3`);
  expect(v3.data).toMatchObject({
    audience: { description: "保存决策生成的新受众版本" },
    status: "draft",
    version: 3
  });
});

test("真实绑定、AI 配置与账号 Recipe 贯通并可由 UI 读取", async ({
  page,
  request
}) => {
  test.setTimeout(180_000);
  const chain = await prepareP0MainChain(request);
  const state = readE2eRuntimeState();
  await page.setViewportSize({ width: 1440, height: 900 });
  await waitForAccountShellIdle(page);
  await page.getByRole("link", { name: "AI 与系统设置" }).click();
  await expect(page).toHaveURL(/\/settings\/ai-system$/);

  const textProviderRow = page.locator("tbody tr").filter({
    hasText: "E2E 本地文本 Provider"
  });
  await expect(textProviderRow).toContainText("就绪");
  await expect(page).toHaveURL(/\/settings\/ai-system$/);
  await textProviderRow.getByRole("button", { name: "管理" }).click();
  const providerDetail = page.locator(".ai-detail-panel");
  await expect(providerDetail).toContainText("凭据");
  await expect(providerDetail).not.toContainText("未配置");
  await expect(providerDetail).not.toContainText(state.providerCredential);

  await page.getByRole("button", { name: "模型与能力" }).click();
  const textModelRow = page.locator("tbody tr").filter({
    has: page.locator("strong", { hasText: "tk-e2e-text-1" })
  });
  await expect(textModelRow).toHaveCount(1);
  await expect(textModelRow).toContainText("tk-e2e-text-1");
  await page.getByRole("button", { name: "能力 Route" }).click();
  for (const label of ["脚本生成", "分镜生成"]) {
    const routeRow = page.locator("tbody tr").filter({ hasText: label });
    await expect(routeRow).toContainText("valid");
  }

  await page.getByRole("button", { name: "Prompt 模板" }).click();
  await page.getByRole("button", {
    name: /E2E 脚本生成 Prompt/
  }).click();
  await page.getByRole("button", { name: "打开版本正文" }).click();
  await expect(page.getByText(
    "你是账号定位驱动的短视频脚本规划助手。",
    { exact: true }
  )).toBeVisible();
  await expect(page.getByText(
    "根据账号知识与选题生成可进入分镜的脚本：{{topic}}",
    { exact: true }
  )).toBeVisible();

  await openAccountManagement(page);
  await openAccountDetail(page, chain.alphaAccountId);
  await page.getByRole("button", { name: "AI 创作档案" }).click();
  const alphaRecipe = page.locator(
    `.recipe-panel[data-account-id="${chain.alphaAccountId}"]`
  );
  await expect(alphaRecipe).toContainText("激活版本");
  await expect(alphaRecipe).toContainText("v1");
  await expect(alphaRecipe).toContainText("账号 Alpha 默认创作 Recipe");

  await openAccountDetail(page, chain.betaAccountId);
  await page.getByRole("button", { name: "AI 创作档案" }).click();
  const betaRecipe = page.locator(
    `.recipe-panel[data-account-id="${chain.betaAccountId}"]`
  );
  await expect(betaRecipe.getByRole("button", {
    name: "创建首个 Recipe"
  })).toBeVisible();
  await expect(betaRecipe).not.toContainText(
    "账号 Alpha 默认创作 Recipe"
  );
});

test("当前账号只接收自身 Runtime 事件并刷新账号上下文", async ({
  page,
  request
}) => {
  const receivedFrames: string[] = [];
  page.on("websocket", (socket) => {
    socket.on("framereceived", ({ payload }) => {
      receivedFrames.push(
        typeof payload === "string"
          ? payload
          : payload.toString("utf8")
      );
    });
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/workspace");
  await selectAccount(page, "账号 Alpha");
  const alpha = await findAccount(request, "alpha_creator");
  const beta = await findAccount(request, "beta_creator");
  await expect.poll(() => receivedFrames.join("\n"))
    .toContain(alpha.id);
  receivedFrames.length = 0;

  await callRuntime(request, `/api/v1/accounts/${beta.id}`, {
    data: { username: "beta_event_only" },
    expectedRevision: beta.revision,
    method: "PATCH"
  });
  await page.waitForTimeout(500);
  expect(receivedFrames.join("\n")).not.toContain(beta.id);
  await expect(page.locator(".account-switcher__trigger"))
    .not.toContainText("@beta_event_only");

  await callRuntime(request, `/api/v1/accounts/${alpha.id}`, {
    data: { username: "alpha_event_visible" },
    expectedRevision: alpha.revision,
    method: "PATCH"
  });
  await expect.poll(() => receivedFrames.join("\n"))
    .toContain(alpha.id);
  await expect(page.locator(".account-switcher__trigger"))
    .toContainText("@alpha_event_visible");

  await selectAccount(page, "账号 Beta");
  await expect(page.locator(".account-switcher__trigger"))
    .toContainText("@beta_event_only");
  await expect(page.getByText("@alpha_event_visible")).toHaveCount(0);

  receivedFrames.length = 0;
  const latestAlpha = await findAccount(request, "alpha_event_visible");
  await callRuntime(request, `/api/v1/accounts/${latestAlpha.id}`, {
    data: { username: "alpha_event_hidden_from_beta" },
    expectedRevision: latestAlpha.revision,
    method: "PATCH"
  });
  await page.waitForTimeout(500);
  expect(receivedFrames.join("\n")).not.toContain(latestAlpha.id);
  await expect(page.locator(".account-switcher__trigger"))
    .toContainText("@beta_event_only");
});

test("归档退出当前账号，恢复任务完成后账号重新可选", async ({
  page,
  request
}) => {
  const alpha = await findAccount(
    request,
    "alpha_event_hidden_from_beta"
  );
  const connectionBeforeArchive = await callRuntime<{
    deviceWorkspace: { id: string } | null;
    browserInstance: { id: string } | null;
    executionBinding: { id: string } | null;
  }>(request, `/api/v1/accounts/${alpha.id}/connection`);
  expect(connectionBeforeArchive.data.deviceWorkspace).not.toBeNull();
  expect(connectionBeforeArchive.data.browserInstance).not.toBeNull();
  expect(connectionBeforeArchive.data.executionBinding).not.toBeNull();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/workspace");
  await selectAccount(page, "账号 Alpha");
  await openAccountManagement(page);
  await openAccountDetail(page, alpha.id);
  await page.getByRole("button", { name: "归档", exact: true }).click();
  await page.getByLabel("归档原因").fill("E2E 生命周期复检");
  const archiveResponsePromise = page.waitForResponse((response) =>
    response.url().endsWith(`/api/v1/accounts/${alpha.id}/archive`)
    && response.request().method() === "POST"
  );
  await page.getByRole("button", { name: "确认归档" }).click();
  const archiveResponse = await archiveResponsePromise;
  expect(archiveResponse.ok()).toBe(true);
  const archivePayload = await archiveResponse.json() as {
    data: { taskId: string };
  };
  await waitForRuntimeTask(
    request,
    archivePayload.data.taskId,
    alpha.id
  );
  await expect.poll(async () => (await getAccount(request, alpha.id)).status)
    .toBe("archived");

  await page.getByRole("link", { name: "工作台" }).click();
  await expect(page.getByText("选择一个账号工作区")).toBeVisible();
  await expect(page.locator(".account-switcher__trigger"))
    .not.toContainText("账号 Alpha");

  await openAccountManagement(page);
  await page.getByLabel("账号状态筛选").selectOption("archived");
  await page.getByRole("button", { name: "应用" }).click();
  await openAccountDetail(page, alpha.id);
  const restoreResponsePromise = page.waitForResponse((response) =>
    response.url().endsWith(`/api/v1/accounts/${alpha.id}/restore`)
    && response.request().method() === "POST"
  );
  await page.getByRole("button", { name: "提交恢复" }).click();
  const restoreResponse = await restoreResponsePromise;
  expect(restoreResponse.ok()).toBe(true);
  const restorePayload = await restoreResponse.json() as {
    data: { taskId: string };
  };
  await expect(page.getByText(`任务：${restorePayload.data.taskId}`))
    .toBeVisible();
  await waitForRuntimeTask(
    request,
    restorePayload.data.taskId,
    alpha.id
  );

  await page.getByRole("button", { name: "刷新列表" }).click();
  await page.getByLabel("账号状态筛选").selectOption("");
  await page.getByRole("button", { name: "应用" }).click();
  await expect(page.locator(`tr[data-account-id="${alpha.id}"]`))
    .toContainText("账号 Alpha");
  expect((await getAccount(request, alpha.id)).status).not.toBe("archived");

  const restoredConnection = await callRuntime<{
    accountId: string;
    deviceWorkspace: { id: string } | null;
    browserInstance: { id: string } | null;
    executionBinding: { id: string } | null;
  }>(request, `/api/v1/accounts/${alpha.id}/connection`);
  expect(restoredConnection.data).toMatchObject({
    accountId: alpha.id,
    browserInstance: null,
    deviceWorkspace: null,
    executionBinding: null
  });
  const restoredEnvironments = await callRuntime<{
    items: Array<{
      browser: { id: string; status: string };
      id: string;
      status: string;
      workspace: { id: string; status: string };
    }>;
  }>(request, `/api/v1/accounts/${alpha.id}/execution-environments`);
  expect(restoredEnvironments.data.items).toContainEqual(
    expect.objectContaining({
      browser: expect.objectContaining({
        id: connectionBeforeArchive.data.browserInstance!.id,
        status: "stopped"
      }),
      id: connectionBeforeArchive.data.executionBinding!.id,
      status: "inactive",
      workspace: expect.objectContaining({
        id: connectionBeforeArchive.data.deviceWorkspace!.id,
        status: "offline"
      })
    })
  );

  const restoredRecipes = await callRuntime<{
    items: Array<{
      accountId: string;
      name: string;
      version: number;
    }>;
  }>(request, `/api/v1/accounts/${alpha.id}/ai-recipe/versions`);
  expect(restoredRecipes.data.items).toContainEqual(
    expect.objectContaining({
      accountId: alpha.id,
      name: "账号 Alpha 默认创作 Recipe",
      version: 1
    })
  );

  const beta = await findAccount(request, "beta_event_only");
  const betaRecipes = await callRuntime<{ items: unknown[] }>(
    request,
    `/api/v1/accounts/${beta.id}/ai-recipe/versions`
  );
  expect(beta.status).not.toBe("archived");
  expect(betaRecipes.data.items).toEqual([]);

  await page.getByRole("link", { name: "工作台" }).click();
  await selectAccount(page, "账号 Alpha");
  await expect(page.getByRole("heading", { name: "账号 Alpha" }))
    .toBeVisible();
});

test("十三个正式容器可达且旧入口只做迁移重定向", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const routes = [
    ["/workspace", "工作台"],
    ["/strategy-knowledge", "定位与知识"],
    ["/scripts", "脚本与选题"],
    ["/storyboards", "分镜规划"],
    ["/video-deconstruction", "视频拆解"],
    ["/production/batches", "批量生产"],
    ["/content-library", "内容库"],
    ["/media-tools", "媒体工具箱"],
    ["/publishing", "发布"],
    ["/review", "复盘"],
    ["/settings/accounts", "账号管理"],
    ["/settings/ai-system", "AI 与系统设置"]
  ] as const;

  for (const [path, title] of routes) {
    await page.goto(path);
    await expect(page).toHaveURL(new RegExp(`${escapePath(path)}(?:\\?|$)`));
    await expect(page.getByText(title, { exact: true }).first())
      .toBeVisible();
  }

  await page.goto("/setup/license?preview=1");
  await expect(page).toHaveURL(/\/setup\/license\?preview=1/);
  await expect(page.getByRole("heading", { name: "准备 TK-OPS" }))
    .toBeVisible();

  await page.goto("/workspace/editing?clip=shot-1#preview");
  await expect(page).toHaveURL(
    /\/production\/batches\?.*clip=shot-1.*#preview/
  );
  await expect(page.getByTestId("legacy-route-notice"))
    .toContainText("旧 AI 剪辑工作台已退出主线");
});

test("主题与两档 PC 窗口布局保持正式壳行为", async (
  { page },
  testInfo
) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/workspace");
  const shell = page.locator(".account-workspace-shell");
  const sidebar = page.locator(".account-sidebar");
  const switchMask = page.locator(".account-workspace-switch-mask");

  await expect(shell).toBeVisible();
  await expect(switchMask).toBeHidden();
  await expect(page.getByTestId("account-workspace-home")).toBeVisible();
  expect((await sidebar.boundingBox())?.width).toBeGreaterThan(200);
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.screenshot({
    animations: "disabled",
    path: testInfo.outputPath("light-1440x900.png")
  });
  const darkAction = page.getByRole("button", {
    name: "切换深色主题"
  });
  await darkAction.click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.screenshot({
    animations: "disabled",
    path: testInfo.outputPath("dark-1440x900.png")
  });
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(switchMask).toBeHidden();
  await expect(page.getByTestId("account-workspace-home")).toBeVisible();

  await page.setViewportSize({ width: 1180, height: 760 });
  await expect(shell).toBeVisible();
  expect((await sidebar.boundingBox())?.width).toBeLessThan(100);
  await expect(page.locator(".account-workspace-too-narrow"))
    .toBeHidden();
  await page.screenshot({
    animations: "disabled",
    path: testInfo.outputPath("dark-1180x760.png")
  });
});

async function selectAccount(page: Page, name: string): Promise<void> {
  const trigger = page.locator(".account-switcher__trigger");
  const menu = page.getByRole("dialog", { name: "切换账号" });
  if ((await trigger.innerText()).includes(name)) return;

  for (let attempt = 0; attempt < 3; attempt += 1) {
    await expect(trigger).toBeEnabled();
    if (!await openAccountMenuAfterRefresh(trigger, menu)) continue;
    const option = menu.locator(".account-switcher__option")
      .filter({ hasText: name });
    try {
      await expect(option).toBeEnabled({ timeout: 2_000 });
      await option.click({ timeout: 2_000 });
    } catch (error) {
      if ((await trigger.innerText()).includes(name)) break;
      await expect(trigger).toBeEnabled();
      if (attempt === 2) throw error;
      continue;
    }
    await expect(trigger).toContainText(name, { timeout: 30_000 });
    break;
  }

  await expect(trigger).toContainText(name);
  await expect(page.locator(".account-workspace-switch-mask")).toBeHidden();
  await expect(trigger).toBeEnabled();
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

async function waitForAccountShellIdle(page: Page): Promise<void> {
  const trigger = page.locator(".account-switcher__trigger");
  await expect(trigger).toBeVisible();
  await expect(trigger).toBeEnabled({ timeout: 30_000 });
  await expect(page.locator(".account-workspace-switch-mask"))
    .toBeHidden({ timeout: 30_000 });
}

async function ensureWorkspaceReady(page: Page): Promise<void> {
  const state = readE2eRuntimeState();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/workspace");
  const licenseInput = page.getByLabel("许可证密钥");
  if (await licenseInput.isVisible()) {
    await licenseInput.fill(state.licenseKey);
    await page.getByRole("button", { name: "激活并继续" }).click();
    await expect(page.getByRole("heading", {
      name: /初始化本地目录|运行环境自检|本机环境已就绪/
    })).toBeVisible({ timeout: 30_000 });
  }
  const directoryStep = page.getByRole("heading", {
    name: "初始化本地目录"
  });
  if (await directoryStep.isVisible()) {
    await page.getByRole("button", { name: "初始化目录" }).click();
    await expect(page.getByRole("heading", {
      name: /运行环境自检|本机环境已就绪/
    })).toBeVisible({ timeout: 30_000 });
  }
  const selfCheck = page.getByRole("heading", { name: "运行环境自检" });
  if (await selfCheck.isVisible()) {
    await page.getByRole("button", { name: "开始自检" }).click();
    await expect(page.getByRole("heading", { name: "本机环境已就绪" }))
      .toBeVisible({ timeout: 90_000 });
  }
  const readyHeading = page.getByRole("heading", { name: "本机环境已就绪" });
  if (await readyHeading.isVisible()) {
    await page.getByRole("button", { name: "进入工作区" }).click();
  }
  await expect(page).toHaveURL(/\/workspace$/);
  await expect(page.locator(".account-switcher__trigger")).toBeVisible();
}

async function ensureAccountFixtures(
  request: Parameters<typeof callRuntime>[0]
): Promise<void> {
  const existing = await callRuntime<{
    items: Array<{ name: string }>;
  }>(request, "/api/v1/accounts?limit=200");
  for (const account of [
    { key: "alpha", name: "账号 Alpha", username: "alpha_creator" },
    { key: "beta", name: "账号 Beta", username: "beta_creator" }
  ]) {
    if (existing.data.items.some((item) => item.name === account.name)) {
      continue;
    }
    await callRuntime(request, "/api/v1/accounts", {
      data: {
        name: account.name,
        platform: "tiktok",
        username: account.username
      },
      idempotencyKey: `e2e-account-${account.key}`,
      method: "POST"
    });
  }
}

async function beginDirtyAccountSwitch(
  page: Page,
  name: string
): Promise<void> {
  const trigger = page.locator(".account-switcher__trigger");
  const menu = page.getByRole("dialog", { name: "切换账号" });
  const prompt = page.getByRole("dialog", { name: "仍有未保存内容" });

  for (let attempt = 0; attempt < 3; attempt += 1) {
    await expect(trigger).toBeEnabled();
    if (!await openAccountMenuAfterRefresh(trigger, menu)) continue;
    const option = menu.locator(".account-switcher__option")
      .filter({ hasText: name });
    try {
      await expect(option).toBeEnabled({ timeout: 2_000 });
      await option.click({ timeout: 2_000 });
    } catch (error) {
      if ((await trigger.innerText()).includes(name)) throw error;
      await expect(trigger).toBeEnabled();
      continue;
    }
    try {
      await expect(prompt).toBeVisible({ timeout: 1_000 });
      return;
    } catch (error) {
      if ((await trigger.innerText()).includes(name)) {
        throw new Error("未保存守卫未触发，账号已直接切换。", {
          cause: error
        });
      }
      await expect(trigger).not.toContainText(name);
      await expect(trigger).toBeEnabled();
    }
  }

  throw new Error("后台刷新结束后仍无法打开未保存决策窗口。");
}

async function fillPositioningEditor(
  page: Page,
  audience: string
): Promise<void> {
  await page.getByLabel("目标受众").fill(audience);
  await page.getByLabel("表达风格").fill("直接、克制、有证据");
  await page.getByLabel(/内容支柱/).fill("产品拆解\n增长实验\nAI 工作流");
  await page.getByText("补充边界", { exact: true }).click();
  await page.getByLabel("禁用主题").fill("未经验证的收益承诺");
  await page.getByLabel("发布约束").fill("结论必须附带来源");
}

async function openAccountDetail(
  page: Page,
  accountId: string
): Promise<void> {
  await page.locator(`tr[data-account-id="${accountId}"]`).click();
  await expect(page.locator(
    `.account-detail[data-account-id="${accountId}"]`
  )).toBeVisible();
}

function escapePath(path: string): string {
  return path.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
