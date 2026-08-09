import {
  expect,
  test,
  type Locator,
  type Page
} from "@playwright/test";

import { readE2eRuntimeState } from "./support/runtime-state";
import { callRuntime } from "./support/runtime-api";
import { registerE2eWorkspaceRoot } from "./support/workspace-root-registry";

test("真实首启链完成授权且不注入执行环境", async ({ page }) => {
  const state = readE2eRuntimeState();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/workspace");

  await expect(page).toHaveURL(/\/setup\/license/);
  await expect(
    page.getByRole("heading", { name: "激活许可证" })
  ).toBeVisible();
  await expect(page.getByText(state.machineCode, { exact: true }))
    .toBeVisible();
  await expect(page.getByText("无需手动填写机器码。", { exact: false }))
    .toBeVisible();
  await page.getByLabel("许可证密钥").fill(state.licenseKey);
  await page.getByRole("button", { name: "激活并继续" }).click();

  const directoryStep = page.getByRole("heading", {
    name: "初始化本地目录"
  });
  if (await waitUntilVisible(directoryStep)) {
    await page.getByRole("button", { name: "初始化目录" }).click();
  }
  await completeSelfCheckWhenRequired(page);
  await expect(
    page.getByRole("heading", { name: "本机环境已就绪" })
  ).toBeVisible({ timeout: 90_000 });

  await page.getByRole("button", { name: "进入工作区" }).click();
  await expect(page).toHaveURL(/\/workspace$/);
  await expect(page.getByText("选择一个账号工作区")).toBeVisible();
});

test("账号切换器在两档 PC 窗口完整可见", async ({ page }) => {
  await ensureWorkspaceReady(page);

  for (const viewport of [
    { width: 1440, height: 900, minimumLeft: 12 },
    { width: 1024, height: 768, minimumLeft: 76 }
  ]) {
    await page.setViewportSize(viewport);
    const trigger = page.locator(".account-switcher__trigger");
    await trigger.click();
    const menu = page.getByRole("dialog", { name: "切换账号" });
    await expect(menu).toBeVisible();
    const bounds = await menu.boundingBox();
    expect(bounds).not.toBeNull();
    if (bounds) {
      expect(bounds.x).toBeGreaterThanOrEqual(viewport.minimumLeft);
      expect(bounds.y).toBeGreaterThanOrEqual(12);
      expect(bounds.x + bounds.width).toBeLessThanOrEqual(viewport.width - 12);
      expect(bounds.y + bounds.height).toBeLessThanOrEqual(viewport.height - 12);
    }
    const hasHorizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth
    );
    expect(hasHorizontalOverflow).toBe(false);
    await page.keyboard.press("Escape");
    await expect(menu).toBeHidden();
  }
});

test("新账号建立环境并完成监督登录", async ({ page, request }) => {
  await ensureWorkspaceReady(page);
  await page.goto("/settings/accounts?action=add");
  const wizard = page.getByRole("dialog", { name: "添加账号" });
  await expect(wizard).toBeVisible();
  await wizard.getByLabel("账号名称").fill("E2E 监督登录账号");
  await wizard.getByLabel(/TikTok 用户名/).fill("e2e_login_account");
  const createResponsePromise = page.waitForResponse((response) =>
    response.url().endsWith("/api/v1/accounts")
    && response.request().method() === "POST"
  );
  await wizard.getByRole("button", { name: "创建草稿并继续" }).click();
  const createPayload = await createResponsePromise.then((response) => response.json()) as {
    data: { id: string };
  };
  const accountId = createPayload.data.id;
  const workspaceRoot = await registerE2eWorkspaceRoot(accountId);
  await page.evaluate((root) => {
    const target = window as Window & {
      __TAURI_INTERNALS__?: {
        invoke(command: string): Promise<unknown>;
      };
    };
    target.__TAURI_INTERNALS__ = {
      async invoke(command: string): Promise<unknown> {
        if (command === "pick_account_workspace_root") return root;
        throw new Error(`E2E 未实现 Tauri 命令：${command}`);
      }
    };
  }, workspaceRoot);

  await expect(wizard.getByText("还没有执行环境")).toBeVisible();
  await wizard.getByRole("button", { name: "新建执行环境" }).click();
  await wizard.getByRole("button", { name: "选择目录" }).click();
  await expect(wizard.getByText(workspaceRoot.displayPath, { exact: true }))
    .toBeVisible();
  await wizard.getByRole("button", { name: "创建执行环境" }).click();
  await expect(wizard.getByText("登录 TikTok", { exact: true }))
    .toBeVisible({ timeout: 120_000 });

  await wizard.getByRole("button", { name: "打开浏览器登录" }).click();
  await expect(wizard.getByText("请在浏览器中自行登录", { exact: true }))
    .toBeVisible({ timeout: 35_000 });
  await wizard.getByRole("button", { name: "我已完成登录" }).click();
  await expect(wizard.getByText("完成账号定位", { exact: true }))
    .toBeVisible({ timeout: 30_000 });

  const connection = await callRuntime<{
    accountId: string;
    authStatus: string;
    executionBinding: { id: string } | null;
    healthStatus: string;
  }>(request, `/api/v1/accounts/${accountId}/connection`);
  expect(connection.data).toMatchObject({
    accountId,
    authStatus: "valid",
    executionBinding: { id: expect.any(String) },
    healthStatus: "ready"
  });
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
  await completeSelfCheckWhenRequired(page);
  const readyHeading = page.getByRole("heading", { name: "本机环境已就绪" });
  if (await waitUntilVisible(readyHeading)) {
    await page.getByRole("button", { name: "进入工作区" }).click();
  }
  await expect(page).toHaveURL(/\/workspace$/);
  await expect(page.getByText("选择一个账号工作区")).toBeVisible();
}

async function completeSelfCheckWhenRequired(page: Page): Promise<void> {
  const selfCheck = page.getByRole("heading", {
    name: "运行环境自检"
  });
  if (await waitUntilVisible(selfCheck)) {
    await page.getByRole("button", { name: "开始自检" }).click();
  }
}

async function waitUntilVisible(locator: Locator): Promise<boolean> {
  return locator.waitFor({ state: "visible", timeout: 15_000 })
    .then(() => true)
    .catch(() => false);
}
