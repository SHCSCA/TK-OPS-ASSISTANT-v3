import {
  createMemoryHistory,
  createRouter,
  type Router
} from "vue-router";
import { describe, expect, it, vi } from "vitest";

import {
  AccountContextApplication
} from "@/app/account-context/application";
import type {
  AccountSurfacePrepareRequest,
  ReversibleAccountSwitchResource
} from "@/app/account-context/types";
import type {
  AccountDto,
  AccountWorkspaceContextDto
} from "@/types/runtime/accounts";

describe("P0 账号路由未保存守卫", () => {
  it("普通路由离开存在脏数据时，取消会留在当前页面", async () => {
    const { application, router } = await createApplication("/workspace");
    application.context.state.currentAccountId = "account-current";
    const unregister = application.unsavedGuards.register({
      id: "script-draft",
      label: "脚本草稿",
      isDirty: () => true,
      save: vi.fn(),
      discard: vi.fn()
    });

    const navigation = router.push("/scripts");
    await waitForPendingDecision(application);
    application.unsavedDecision.resolve("cancel");
    await navigation;

    expect(router.currentRoute.value.path).toBe("/workspace");
    unregister();
    await application.dispose();
  });

  it("普通路由离开保存成功后允许进入目标页面", async () => {
    const { application, router } = await createApplication("/workspace");
    application.context.state.currentAccountId = "account-current";
    let dirty = true;
    const save = vi.fn(async () => {
      dirty = false;
    });
    const unregister = application.unsavedGuards.register({
      id: "topic-draft",
      label: "选题草稿",
      isDirty: () => dirty,
      save,
      discard: vi.fn()
    });

    const navigation = router.push("/scripts");
    await waitForPendingDecision(application);
    application.unsavedDecision.resolve("save");
    await navigation;

    expect(save).toHaveBeenCalledOnce();
    expect(router.currentRoute.value.path).toBe("/scripts");
    unregister();
    await application.dispose();
  });

  it("账号切换内部提交路由时不重复触发 route-leave 守卫", async () => {
    const { application, router } = await createApplication("/workspace");
    application.context.state.currentAccountId = "account-source";
    vi.spyOn(application.uiConfig, "setActiveAccount").mockResolvedValue();
    const guard = vi.spyOn(application.context, "guardUnsaved");
    const context = workspaceContext("account-target");
    const internal = application as unknown as {
      prepareSurface(
        request: AccountSurfacePrepareRequest<AccountWorkspaceContextDto>
      ): Promise<ReversibleAccountSwitchResource>;
    };

    const resource = await internal.prepareSurface({
      accountId: "account-target",
      scopeKey: "account:account-target",
      switchIntentId: "switch-account-target",
      switchRevision: 1,
      signal: new AbortController().signal,
      previousContext: workspaceContext("account-source"),
      context,
      preferredRoute: "/scripts",
      accountRevision: 2
    });
    await resource.commit();

    expect(router.currentRoute.value.path).toBe("/scripts");
    expect(guard).not.toHaveBeenCalled();
    await resource.finalize?.();
    await application.dispose();
  });
});

async function createApplication(initialPath: string): Promise<{
  application: AccountContextApplication;
  router: Router;
}> {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/workspace",
        name: "account_workspace_home",
        component: { template: "<section />" }
      },
      {
        path: "/scripts",
        name: "account_script_topic",
        component: { template: "<section />" }
      }
    ]
  });
  await router.push(initialPath);
  await router.isReady();
  const application = new AccountContextApplication();
  vi.spyOn(application.context, "rememberRoute").mockResolvedValue();
  application.configureRouter(router);
  return { application, router };
}

async function waitForPendingDecision(
  application: AccountContextApplication
): Promise<void> {
  for (let attempt = 0; attempt < 8; attempt += 1) {
    if (application.unsavedDecision.state.pending) return;
    await Promise.resolve();
  }
  throw new Error("路由未保存守卫没有进入待决状态。");
}

function workspaceContext(accountId: string): AccountWorkspaceContextDto {
  const readinessItem = {
    status: "ready" as const,
    label: "已就绪",
    errorCode: null,
    logId: null,
    checkedAt: null,
    suggestedAction: null
  };
  const account: AccountDto = {
    id: accountId,
    name: "测试账号",
    username: null,
    platform: "tiktok",
    status: "ready",
    positioningSummary: null,
    lastUsedAt: null,
    readiness: {
      connection: { ...readinessItem },
      knowledge: { ...readinessItem },
      ai: { ...readinessItem },
      overall: "ready",
      checkedAt: null,
      suggestedAction: null
    },
    wizardCompletedAt: null,
    revision: 1
  };
  return {
    account,
    readiness: account.readiness,
    navigation: {
      lastRoute: "/workspace",
      availableRoutes: [
        "account_workspace_home",
        "account_script_topic"
      ]
    },
    taskSummary: {
      running: 0,
      failed: 0
    },
    workspaceRevision: 1
  };
}
