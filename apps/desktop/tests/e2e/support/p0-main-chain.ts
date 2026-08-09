import { expect, type APIRequestContext } from "@playwright/test";

import {
  callRuntime,
  waitForRuntimeTask
} from "./runtime-api";
import { readE2eRuntimeState } from "./runtime-state";
import { registerE2eWorkspaceRoot } from "./workspace-root-registry";

type Account = {
  id: string;
  name: string;
  revision: number;
  status: string;
  username: string | null;
};

type Provider = {
  credentialSummary: {
    configured: boolean;
    maskedValue: string | null;
  };
  healthStatus: string;
  id: string;
  revision: number;
};

type Model = {
  capabilities: Array<{
    availability: string;
    capabilityKey: string;
    contractVerified: boolean;
  }>;
  id: string;
  modelId: string;
  revision: number;
};

type TaskAccepted = {
  taskId: string;
};

type ExecutionEnvironmentAccepted = TaskAccepted & {
  environmentId: string;
};

type PromptProfile = {
  activeVersion: number | null;
  activeVersionId: string | null;
  profileKey: string;
  revision: number;
};

export type P0MainChainContext = {
  alphaAccountId: string;
  betaAccountId: string;
  promptProfileKey: string;
  textModelId: string;
  videoModelId: string;
};

export async function prepareP0MainChain(
  request: APIRequestContext
): Promise<P0MainChainContext> {
  const alpha = await findAccount(request, "alpha_creator");
  const beta = await findAccount(request, "beta_creator");
  const workspaceRoot = await registerE2eWorkspaceRoot(alpha.id);
  const environment = await callRuntime<ExecutionEnvironmentAccepted>(
    request,
    `/api/v1/accounts/${alpha.id}/execution-environments`,
    {
      data: {
        activateWhenReady: false,
        browser: { kind: "chrome", selection: "auto" },
        name: "E2E Alpha 执行环境",
        rootRef: workspaceRoot.rootRef
      },
      idempotencyKey: "e2e-environment-alpha",
      method: "POST"
    }
  );
  await waitForRuntimeTask(request, environment.data.taskId, alpha.id);
  const candidates = await callRuntime<{
    items: Array<{
      eligibilityRevision: number;
      environmentId: string;
      browserInstance: { id: string; status: string };
      deviceWorkspace: { id: string };
      executionBinding: { id: string };
    }>;
  }>(request, `/api/v1/accounts/${alpha.id}/connection/candidates`);
  const candidate = candidates.data.items.find(
    (item) => item.environmentId === environment.data.environmentId
  );
  expect(candidate).toEqual(expect.objectContaining({
    eligibilityRevision: expect.any(Number),
    environmentId: expect.any(String),
    browserInstance: expect.objectContaining({ id: expect.any(String) }),
    deviceWorkspace: expect.objectContaining({ id: expect.any(String) }),
    executionBinding: expect.objectContaining({ id: expect.any(String) })
  }));
  if (!candidate) throw new Error("执行环境创建成功后未进入账号连接候选。");

  const refreshedForBinding = await getAccount(request, alpha.id);
  const bound = await callRuntime<{
    accountId: string;
    browserInstance: { id: string; status: string };
    deviceWorkspace: { id: string };
    executionBinding: { id: string };
    lastCheck: {
      checkedAt: string | null;
      errorCode: string | null;
      logId: string | null;
      status: string;
    } | null;
  }>(request, `/api/v1/accounts/${alpha.id}/connection/binding`, {
    data: {
      eligibilityRevision: candidate.eligibilityRevision,
      environmentId: candidate.environmentId
    },
    expectedRevision: refreshedForBinding.revision,
    idempotencyKey: "e2e-bind-alpha",
    method: "PUT"
  });
  expect(bound.data).toMatchObject({
    accountId: alpha.id,
    browserInstance: {
      id: candidate.browserInstance.id
    },
    deviceWorkspace: { id: candidate.deviceWorkspace.id },
    executionBinding: { id: candidate.executionBinding.id },
    lastCheck: {
      checkedAt: null,
      errorCode: null,
      logId: null,
      status: "unknown"
    }
  });

  const ai = await configureAI(request);
  const refreshedAlpha = await getAccount(request, alpha.id);
  const createdRecipe = await callRuntime<{
    accountId: string;
    validationStatus: string;
    version: number;
  }>(request, `/api/v1/accounts/${alpha.id}/ai-recipe/versions`, {
    data: {
      compositionTemplateRef: null,
      costPolicy: {},
      fallbackPolicy: {},
      name: "账号 Alpha 默认创作 Recipe",
      routeOverrides: {},
      visualStyle: {},
      voiceProfileRef: null
    },
    expectedRevision: refreshedAlpha.revision,
    idempotencyKey: "e2e-recipe-alpha-v1",
    method: "POST"
  });
  expect(createdRecipe.data).toMatchObject({
    accountId: alpha.id,
    validationStatus: "unvalidated",
    version: 1
  });

  const validation = await callRuntime<{
    resolvedRouteSummary: Record<string, {
      source: string;
    }>;
    validationStatus: string;
  }>(
    request,
    `/api/v1/accounts/${alpha.id}/ai-recipe/versions/1/validate`,
    {
      idempotencyKey: "e2e-recipe-alpha-v1-validate",
      method: "POST"
    }
  );
  expect(validation.data.validationStatus).toBe("valid");
  for (const capability of [
    "script_generation",
    "storyboard_generation",
    "text_to_video"
  ]) {
    expect(validation.data.resolvedRouteSummary[capability]?.source)
      .toBe("system");
  }
  const activatedRecipe = await callRuntime<{
    accountId: string;
    activeVersion: number | null;
    resolvedSummary: Record<string, unknown> | null;
  }>(request, `/api/v1/accounts/${alpha.id}/ai-recipe/versions/1/activate`, {
    expectedRevision: requireRevision(validation.meta.revision),
    idempotencyKey: "e2e-recipe-alpha-v1-activate",
    method: "POST"
  });
  expect(activatedRecipe.data).toMatchObject({
    accountId: alpha.id,
    activeVersion: 1
  });
  expect(activatedRecipe.data.resolvedSummary).not.toBeNull();

  const betaVersions = await callRuntime<{ items: unknown[] }>(
    request,
    `/api/v1/accounts/${beta.id}/ai-recipe/versions`
  );
  expect(betaVersions.data.items).toEqual([]);
  await assertProviderBoundaryEvidence(request);
  return {
    alphaAccountId: alpha.id,
    betaAccountId: beta.id,
    promptProfileKey: ai.promptProfileKey,
    textModelId: ai.textModelId,
    videoModelId: ai.videoModelId
  };
}

async function configureAI(request: APIRequestContext): Promise<{
  promptProfileKey: string;
  textModelId: string;
  videoModelId: string;
}> {
  const state = readE2eRuntimeState();
  const textProvider = await createReadyProvider(
    request,
    "E2E 本地文本 Provider",
    "openai_compatible",
    `${state.providerBaseUrl}/v1`,
    "text"
  );
  const videoProvider = await createReadyProvider(
    request,
    "E2E 本地视频 Provider",
    "comfyui",
    state.providerBaseUrl,
    "video"
  );
  const textModel = await createVerifiedModel(
    request,
    textProvider.id,
    "tk-e2e-text-1",
    "E2E 文本能力模型",
    ["script_generation", "storyboard_generation"],
    "text"
  );
  const videoModel = await createVerifiedModel(
    request,
    videoProvider.id,
    "tk-e2e-video-1",
    "E2E 视频能力模型",
    ["text_to_video"],
    "video"
  );
  const prompt = await createActivePrompt(request);
  await putRoute(
    request,
    "script_generation",
    textModel.id,
    prompt.activeVersionId
  );
  await putRoute(
    request,
    "storyboard_generation",
    textModel.id,
    null
  );
  await putRoute(
    request,
    "text_to_video",
    videoModel.id,
    null
  );
  return {
    promptProfileKey: prompt.profileKey,
    textModelId: textModel.id,
    videoModelId: videoModel.id
  };
}

async function createReadyProvider(
  request: APIRequestContext,
  name: string,
  adapterType: "openai_compatible" | "comfyui",
  baseUrl: string,
  key: string
): Promise<Provider> {
  const state = readE2eRuntimeState();
  const created = await callRuntime<Provider>(
    request,
    "/api/v1/system/providers",
    {
      data: {
        adapterType,
        baseUrl,
        enabled: true,
        maxConcurrency: 1,
        name,
        region: null,
        timeoutMs: 5_000
      },
      idempotencyKey: `e2e-provider-${key}`,
      method: "POST"
    }
  );
  const credential = await callRuntime<{
    configured: true;
    credentialRef: string;
    maskedValue: string;
    providerRevision: number;
  }>(request, `/api/v1/system/providers/${created.data.id}/credential`, {
    data: { credential: state.providerCredential },
    expectedRevision: created.data.revision,
    method: "PUT"
  });
  expect(credential.data.configured).toBe(true);
  expect(credential.data.credentialRef)
    .toMatch(/^secret:\/\/providers\//);
  expect(credential.data.maskedValue).not.toBe(state.providerCredential);
  expect(JSON.stringify(credential)).not.toContain(state.providerCredential);

  const accepted = await callRuntime<TaskAccepted>(
    request,
    `/api/v1/system/providers/${created.data.id}/checks`,
    {
      data: { force: true },
      idempotencyKey: `e2e-provider-check-${key}`,
      method: "POST"
    }
  );
  await waitForRuntimeTask(request, accepted.data.taskId);
  const ready = await callRuntime<Provider>(
    request,
    `/api/v1/system/providers/${created.data.id}`
  );
  expect(ready.data).toMatchObject({
    credentialSummary: {
      configured: true
    },
    healthStatus: "ready"
  });
  return ready.data;
}

async function createVerifiedModel(
  request: APIRequestContext,
  providerId: string,
  modelId: string,
  displayName: string,
  capabilityKeys: string[],
  key: string
): Promise<Model> {
  const created = await callRuntime<Model>(
    request,
    "/api/v1/system/models",
    {
      data: {
        baseLimits: {},
        displayName,
        enabled: true,
        modelId,
        providerProfileId: providerId
      },
      idempotencyKey: `e2e-model-${key}`,
      method: "POST"
    }
  );
  const accepted = await callRuntime<TaskAccepted>(
    request,
    `/api/v1/system/models/${created.data.id}/capability-checks`,
    {
      data: { capabilityKeys, force: true },
      idempotencyKey: `e2e-model-capabilities-${key}`,
      method: "POST"
    }
  );
  await waitForRuntimeTask(request, accepted.data.taskId);
  const verified = await callRuntime<Model>(
    request,
    `/api/v1/system/models/${created.data.id}`
  );
  for (const capabilityKey of capabilityKeys) {
    expect(verified.data.capabilities).toContainEqual(
      expect.objectContaining({
        availability: "available",
        capabilityKey,
        contractVerified: true
      })
    );
  }
  return verified.data;
}

async function createActivePrompt(
  request: APIRequestContext
): Promise<PromptProfile> {
  const profileKey = "e2e-script-generation";
  const created = await callRuntime<PromptProfile>(
    request,
    "/api/v1/system/prompt-profiles",
    {
      data: {
        capabilityKey: "script_generation",
        name: "E2E 脚本生成 Prompt",
        outputSchema: { type: "object" },
        profileKey,
        safetyConstraints: {},
        systemPrompt: "你是账号定位驱动的短视频脚本规划助手。",
        taskTemplate: "根据账号知识与选题生成可进入分镜的脚本：{{topic}}",
        variablesSchema: {
          properties: { topic: { type: "string" } },
          required: ["topic"],
          type: "object"
        },
        visualStylePrefix: ""
      },
      idempotencyKey: "e2e-prompt-script-generation",
      method: "POST"
    }
  );
  const activated = await callRuntime<PromptProfile>(
    request,
    `/api/v1/system/prompt-profiles/${profileKey}/versions/1/activate`,
    {
      expectedRevision: created.data.revision,
      idempotencyKey: "e2e-prompt-script-generation-activate",
      method: "POST"
    }
  );
  expect(activated.data.activeVersion).toBe(1);
  expect(activated.data.activeVersionId).toBeTruthy();
  return activated.data;
}

async function putRoute(
  request: APIRequestContext,
  capabilityKey: string,
  modelProfileId: string,
  promptProfileId: string | null
): Promise<void> {
  const route = await callRuntime<{
    capabilityKey: string;
    validationStatus: string;
  }>(
    request,
    `/api/v1/system/capability-routes/${capabilityKey}`,
    {
      data: {
        enabled: true,
        fallbackModelProfileId: null,
        primaryModelProfileId: modelProfileId,
        promptProfileId
      },
      expectedRevision: 0,
      idempotencyKey: `e2e-route-${capabilityKey}`,
      method: "PUT"
    }
  );
  expect(route.data).toMatchObject({
    capabilityKey,
    validationStatus: "valid"
  });
}

async function assertProviderBoundaryEvidence(
  request: APIRequestContext
): Promise<void> {
  const state = readE2eRuntimeState();
  const response = await request.get(
    `${state.providerBaseUrl}/__e2e__/evidence`
  );
  expect(response.ok()).toBe(true);
  const evidence = await response.json() as {
    authorizedRequests: number;
    modelsRequests: number;
    systemStatsRequests: number;
  };
  expect(evidence.authorizedRequests).toBeGreaterThanOrEqual(4);
  expect(evidence.modelsRequests).toBeGreaterThanOrEqual(2);
  expect(evidence.systemStatsRequests).toBeGreaterThanOrEqual(2);
}

export async function findAccount(
  request: APIRequestContext,
  username: string
): Promise<Account> {
  const accounts = await callRuntime<{ items: Account[] }>(
    request,
    "/api/v1/accounts?limit=100"
  );
  const account = accounts.data.items.find(
    (item) => item.username === username
  );
  if (!account) throw new Error(`未找到 E2E 账号：${username}`);
  return account;
}

export async function getAccount(
  request: APIRequestContext,
  accountId: string
): Promise<Account> {
  return (
    await callRuntime<Account>(
      request,
      `/api/v1/accounts/${accountId}`
    )
  ).data;
}

function requireRevision(revision: number | undefined): number {
  if (!Number.isInteger(revision) || Number(revision) < 1) {
    throw new Error("Runtime 未返回有效修订号。");
  }
  return Number(revision);
}
