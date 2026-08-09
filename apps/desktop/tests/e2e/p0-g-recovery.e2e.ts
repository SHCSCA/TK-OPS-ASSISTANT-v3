import {
  expect,
  test,
  type APIRequestContext,
  type Locator,
  type Page
} from "@playwright/test";

import { callRuntime } from "./support/runtime-api";
import { readE2eRuntimeState } from "./support/runtime-state";
import {
  registerE2eWorkspaceRoot,
  type E2eWorkspaceRoot
} from "./support/workspace-root-registry";

type AccountDraft = {
  accountId: string;
  wizard: Locator;
};

type EnvironmentAccepted = {
  environmentId: string;
  taskId: string;
};

type EnvironmentDto = {
  browser: { id: string; status: string };
  id: string;
  lastRetryOfTaskId: string | null;
  lastTaskId: string | null;
  recoveryActions: string[];
  revision: number;
  status: string;
  workspace: { id: string; rootRef: string };
};

type LoginSessionAccepted = {
  sessionId: string;
  taskId: string;
};

type LoginSessionDto = {
  id: string;
  prepareTaskId: string | null;
  state: string;
};

type RuntimeTask = {
  completionKind: string | null;
  errorCode: string | null;
  status: string;
  taskId: string;
};

type FaultState = {
  browserLaunchFailureArmed: boolean;
  loginNavigationBlockArmed: boolean;
  loginNavigationReleased: boolean;
  loginNavigationStarted: boolean;
};

test.describe.configure({ mode: "serial" });

test.beforeEach(async ({ page }) => {
  await ensureWorkspaceReady(page);
});

test("执行环境失败会保留原对象并从可见恢复入口重试成功", async ({
  page,
  request
}) => {
  test.setTimeout(180_000);
  const { accountId, wizard } = await createDraftAccount(
    page,
    "E2E 环境恢复账号",
    "e2e_environment_recovery"
  );
  const workspaceRoot = await registerE2eWorkspaceRoot(accountId);
  await installWorkspaceRootBridge(page, workspaceRoot);
  await callRuntime<FaultState>(request, "/__e2e__/faults/browser-launch", {
    method: "POST"
  });

  await wizard.getByRole("button", { name: "新建执行环境" }).click();
  await wizard.getByRole("button", { name: "选择目录" }).click();
  const createResponsePromise = page.waitForResponse((response) =>
    response.url().endsWith(`/api/v1/accounts/${accountId}/execution-environments`)
    && response.request().method() === "POST"
  );
  await wizard.getByRole("button", { name: "创建执行环境" }).click();
  const createPayload = await readSuccessData<EnvironmentAccepted>(
    await createResponsePromise
  );

  await expect(wizard.getByText("恢复执行环境", { exact: true }))
    .toBeVisible({ timeout: 45_000 });
  await expect(wizard.getByText(
    "沿用原工作目录、浏览器实例和任务上下文重试。",
    { exact: true }
  )).toBeVisible();
  await expect(wizard.getByRole("button", { name: "重试创建" }))
    .toBeVisible();
  await expect(wizard.getByRole("button", { name: "查看日志" }))
    .toBeVisible();

  const failedTask = await getAccountTask(
    request,
    accountId,
    createPayload.taskId
  );
  expect(failedTask).toMatchObject({
    errorCode: "EXECUTION_ENVIRONMENT_PROVISION_FAILED",
    status: "failed"
  });
  const failedEnvironment = await getEnvironment(
    request,
    accountId,
    createPayload.environmentId
  );
  expect(failedEnvironment).toMatchObject({
    id: createPayload.environmentId,
    lastTaskId: createPayload.taskId,
    status: "failed",
    workspace: { rootRef: workspaceRoot.rootRef }
  });
  expect(failedEnvironment.recoveryActions).toContain("retry_provision");

  const retryResponsePromise = page.waitForResponse((response) =>
    response.url().endsWith(
      `/api/v1/accounts/${accountId}/execution-environments/${createPayload.environmentId}/retry`
    ) && response.request().method() === "POST"
  );
  await wizard.getByRole("button", { name: "重试创建" }).click();
  const retryPayload = await readSuccessData<EnvironmentAccepted & {
    retryOfTaskId: string;
  }>(await retryResponsePromise);
  await expect(wizard.getByText("登录 TikTok", { exact: true }))
    .toBeVisible({ timeout: 120_000 });

  const recoveredEnvironment = await getEnvironment(
    request,
    accountId,
    createPayload.environmentId
  );
  expect(retryPayload).toMatchObject({
    environmentId: createPayload.environmentId,
    retryOfTaskId: createPayload.taskId
  });
  expect(recoveredEnvironment).toMatchObject({
    browser: {
      id: failedEnvironment.browser.id,
      status: "running"
    },
    id: failedEnvironment.id,
    lastRetryOfTaskId: createPayload.taskId,
    lastTaskId: retryPayload.taskId,
    status: "active",
    workspace: {
      id: failedEnvironment.workspace.id,
      rootRef: failedEnvironment.workspace.rootRef
    }
  });
});

test("监督登录准备阶段取消会终止 Runtime 任务并显示可恢复状态", async ({
  page,
  request
}) => {
  test.setTimeout(180_000);
  const { accountId, wizard } = await createDraftAccount(
    page,
    "E2E 登录取消账号",
    "e2e_login_cancel"
  );
  const workspaceRoot = await registerE2eWorkspaceRoot(accountId);
  await installWorkspaceRootBridge(page, workspaceRoot);
  await wizard.getByRole("button", { name: "新建执行环境" }).click();
  await wizard.getByRole("button", { name: "选择目录" }).click();
  await wizard.getByRole("button", { name: "创建执行环境" }).click();
  await expect(wizard.getByText("登录 TikTok", { exact: true }))
    .toBeVisible({ timeout: 120_000 });

  await callRuntime<FaultState>(
    request,
    "/__e2e__/faults/login-navigation/block",
    { method: "POST" }
  );
  const loginResponsePromise = page.waitForResponse((response) =>
    response.url().endsWith(`/api/v1/accounts/${accountId}/connection/login-sessions`)
    && response.request().method() === "POST"
  );
  await wizard.getByRole("button", { name: "打开浏览器登录" }).click();
  const loginPayload = await readSuccessData<LoginSessionAccepted>(
    await loginResponsePromise
  );

  try {
    await expect(wizard.getByText("正在打开受控浏览器", { exact: true }))
      .toBeVisible();
    await expect.poll(async () => {
      const result = await callRuntime<FaultState>(request, "/__e2e__/faults");
      return result.data.loginNavigationStarted;
    }).toBe(true);

    await wizard.getByRole("button", { name: "取消", exact: true }).click();
    await expect(wizard.getByText("登录已取消", { exact: true }))
      .toBeVisible({ timeout: 30_000 });
    await expect(wizard.getByRole("button", { name: "重新开始登录" }))
      .toBeVisible();

    const session = await callRuntime<LoginSessionDto>(
      request,
      `/api/v1/accounts/${accountId}/connection/login-sessions/${loginPayload.sessionId}`
    );
    const task = await getAccountTask(request, accountId, loginPayload.taskId);
    expect(session.data).toMatchObject({
      id: loginPayload.sessionId,
      prepareTaskId: loginPayload.taskId,
      state: "cancelled"
    });
    expect(task).toMatchObject({
      completionKind: "cancelled",
      status: "completed",
      taskId: loginPayload.taskId
    });
  } finally {
    await callRuntime<FaultState>(
      request,
      "/__e2e__/faults/login-navigation/release",
      { method: "POST" }
    );
  }
});

async function createDraftAccount(
  page: Page,
  name: string,
  username: string
): Promise<AccountDraft> {
  await page.goto("/settings/accounts?action=add");
  const wizard = page.getByRole("dialog", { name: "添加账号" });
  await expect(wizard).toBeVisible();
  await wizard.getByLabel("账号名称").fill(name);
  await wizard.getByLabel(/TikTok 用户名/).fill(username);
  const responsePromise = page.waitForResponse((response) =>
    response.url().endsWith("/api/v1/accounts")
    && response.request().method() === "POST"
  );
  await wizard.getByRole("button", { name: "创建草稿并继续" }).click();
  const account = await readSuccessData<{ id: string }>(await responsePromise);
  await expect(wizard.getByText("还没有执行环境", { exact: true }))
    .toBeVisible();
  return { accountId: account.id, wizard };
}

async function installWorkspaceRootBridge(
  page: Page,
  root: E2eWorkspaceRoot
): Promise<void> {
  await page.evaluate((workspaceRoot) => {
    const target = window as Window & {
      __TAURI_INTERNALS__?: {
        invoke(command: string): Promise<unknown>;
      };
    };
    target.__TAURI_INTERNALS__ = {
      async invoke(command: string): Promise<unknown> {
        if (command === "pick_account_workspace_root") return workspaceRoot;
        throw new Error(`E2E 未实现 Tauri 命令：${command}`);
      }
    };
  }, root);
}

async function getEnvironment(
  request: APIRequestContext,
  accountId: string,
  environmentId: string
): Promise<EnvironmentDto> {
  const result = await callRuntime<EnvironmentDto>(
    request,
    `/api/v1/accounts/${accountId}/execution-environments/${environmentId}`
  );
  return result.data;
}

async function getAccountTask(
  request: APIRequestContext,
  accountId: string,
  taskId: string
): Promise<RuntimeTask> {
  const result = await callRuntime<RuntimeTask>(
    request,
    `/api/v1/accounts/${accountId}/tasks/${taskId}`
  );
  return result.data;
}

async function readSuccessData<T>(response: {
  json(): Promise<unknown>;
}): Promise<T> {
  const payload = await response.json() as { data?: T; ok?: boolean };
  if (payload.ok !== true || payload.data === undefined) {
    throw new Error("E2E 请求没有返回成功信封。");
  }
  return payload.data;
}

async function ensureWorkspaceReady(page: Page): Promise<void> {
  const state = readE2eRuntimeState();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/workspace");
  const licenseInput = page.getByLabel("许可证密钥");
  if (await waitUntilVisible(licenseInput)) {
    await licenseInput.fill(state.licenseKey);
    await page.getByRole("button", { name: "激活并继续" }).click();
  }
  const directoryStep = page.getByRole("heading", { name: "初始化本地目录" });
  if (await waitUntilVisible(directoryStep)) {
    await page.getByRole("button", { name: "初始化目录" }).click();
  }
  const selfCheck = page.getByRole("heading", { name: "运行环境自检" });
  if (await waitUntilVisible(selfCheck)) {
    await page.getByRole("button", { name: "开始自检" }).click();
  }
  const readyHeading = page.getByRole("heading", { name: "本机环境已就绪" });
  if (await waitUntilVisible(readyHeading)) {
    await page.getByRole("button", { name: "进入工作区" }).click();
  }
  await expect(page).toHaveURL(/\/workspace$/);
}

async function waitUntilVisible(locator: Locator): Promise<boolean> {
  return locator.waitFor({ state: "visible", timeout: 3_000 })
    .then(() => true)
    .catch(() => false);
}
