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
    "storyboard_generation"
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
    textModelId: ai.textModelId
  };
}

async function configureAI(request: APIRequestContext): Promise<{
  promptProfileKey: string;
  textModelId: string;
}> {
  const textProvider = await createReadyProvider(request);
  const textModel = await discoverAndValidateModel(request, textProvider.id);
  const prompt = await createActivePrompt(request, {
    capabilityKey: "script_generation",
    name: "E2E 脚本生成 Prompt",
    outputSchema: {
      properties: { script: { type: "string" } },
      required: ["script"],
      type: "object"
    },
    profileKey: "e2e-script-generation",
    systemPrompt: "你是账号定位驱动的短视频脚本规划助手。",
    taskTemplate: "根据账号知识与选题生成可进入分镜的脚本：{{topic}}"
  });
  const storyboardPrompt = await createActivePrompt(request, {
    capabilityKey: "storyboard_generation",
    name: "E2E 分镜生成 Prompt",
    outputSchema: {
      properties: {
        shots: { items: { type: "object" }, type: "array" }
      },
      required: ["shots"],
      type: "object"
    },
    profileKey: "e2e-storyboard-generation",
    systemPrompt: "你是短视频分镜规划助手。",
    taskTemplate: "根据主题生成可进入批量生产的镜头清单：{{topic}}"
  });
  await createActiveRoute(
    request,
    "script_generation",
    textModel.id,
    prompt.activeVersionId
  );
  await createActiveRoute(
    request,
    "storyboard_generation",
    textModel.id,
    storyboardPrompt.activeVersionId
  );
  return {
    promptProfileKey: prompt.profileKey,
    textModelId: textModel.id
  };
}

async function createReadyProvider(
  request: APIRequestContext
): Promise<Provider> {
  const state = readE2eRuntimeState();
  const created = await callRuntime<Provider>(
    request,
    "/api/v1/system/providers",
    {
      data: {
        adapterType: "openai_compatible",
        baseUrl: `${state.providerBaseUrl}/v1`,
        costPolicy: {
          inputMicrosPerMillionUnits: 1_000_000,
          outputMicrosPerMillionUnits: 2_000_000,
          pricingRevision: 1
        },
        enabled: true,
        extraParams: { protocolVariant: "chat_completions" },
        maxConcurrency: 1,
        name: "E2E 本地文本 Provider",
        region: null,
        timeoutMs: 5_000
      },
      idempotencyKey: "e2e-provider-text-real",
      method: "POST"
    }
  );
  const credential = await callRuntime<{
    configured: true;
    credentialReferenceChanged: true;
    maskedValue: string;
    providerRevision: number;
  }>(request, `/api/v1/system/providers/${created.data.id}/credential`, {
    data: { credential: state.providerCredential },
    expectedRevision: created.data.revision,
    method: "PUT"
  });
  expect(credential.data.configured).toBe(true);
  expect(credential.data.credentialReferenceChanged).toBe(true);
  expect(credential.data).not.toHaveProperty("credentialRef");
  expect(credential.data.maskedValue).not.toBe(state.providerCredential);
  expect(JSON.stringify(credential)).not.toContain(state.providerCredential);

  const accepted = await callRuntime<TaskAccepted>(
    request,
    `/api/v1/system/providers/${created.data.id}/checks`,
    {
      data: {
        force: true,
        stages: ["network", "authentication"]
      },
      idempotencyKey: "e2e-provider-check-text-real",
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

async function discoverAndValidateModel(
  request: APIRequestContext,
  providerId: string
): Promise<Model> {
  const discovery = await callRuntime<TaskAccepted>(
    request,
    `/api/v1/system/providers/${providerId}/model-discovery`,
    {
      data: { replaceMissing: false },
      idempotencyKey: "e2e-provider-model-discovery-text-real",
      method: "POST"
    }
  );
  await waitForRuntimeTask(request, discovery.data.taskId);
  const models = await callRuntime<{ items: Model[] }>(
    request,
    `/api/v1/system/models?providerId=${encodeURIComponent(providerId)}&limit=100`
  );
  const discovered = models.data.items.find(
    (item) => item.modelId === "tk-e2e-text-1"
  );
  if (!discovered) throw new Error("真实模型发现未返回 E2E 文本模型。");
  const enabled = await callRuntime<Model>(
    request,
    `/api/v1/system/models/${discovered.id}`,
    {
      data: { enabled: true },
      expectedRevision: discovered.revision,
      method: "PATCH"
    }
  );
  const capabilityKeys = ["script_generation", "storyboard_generation"];
  const accepted = await callRuntime<TaskAccepted>(
    request,
    `/api/v1/system/models/${enabled.data.id}/capability-checks`,
    {
      data: {
        capabilityKeys,
        force: true,
        mode: "real_small_call"
      },
      idempotencyKey: "e2e-model-capabilities-text-real",
      method: "POST"
    }
  );
  await waitForRuntimeTask(request, accepted.data.taskId);
  const verified = await callRuntime<Model>(
    request,
    `/api/v1/system/models/${enabled.data.id}`
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
  request: APIRequestContext,
  input: {
    capabilityKey: string;
    name: string;
    outputSchema: Record<string, unknown>;
    profileKey: string;
    systemPrompt: string;
    taskTemplate: string;
  }
): Promise<PromptProfile> {
  const created = await callRuntime<PromptProfile>(
    request,
    "/api/v1/system/prompt-profiles",
    {
      data: {
        capabilityKey: input.capabilityKey,
        name: input.name,
        outputSchema: input.outputSchema,
        profileKey: input.profileKey,
        safetyConstraints: {},
        systemPrompt: input.systemPrompt,
        taskTemplate: input.taskTemplate,
        variablesSchema: {
          properties: { topic: { type: "string" } },
          required: ["topic"],
          type: "object"
        },
        visualStylePrefix: ""
      },
      idempotencyKey: `e2e-prompt-${input.capabilityKey}`,
      method: "POST"
    }
  );
  const activated = await callRuntime<PromptProfile>(
    request,
    `/api/v1/system/prompt-profiles/${input.profileKey}/versions/1/activate`,
    {
      expectedRevision: created.data.revision,
      idempotencyKey: `e2e-prompt-${input.capabilityKey}-activate`,
      method: "POST"
    }
  );
  expect(activated.data.activeVersion).toBe(1);
  expect(activated.data.activeVersionId).toBeTruthy();
  return activated.data;
}

async function createActiveRoute(
  request: APIRequestContext,
  capabilityKey: string,
  modelProfileId: string,
  promptProfileId: string | null
): Promise<void> {
  const created = await callRuntime<{
    revision: number;
    status: string;
  }>(
    request,
    `/api/v1/system/capability-routes/${capabilityKey}/revisions`,
    {
      data: {
        candidates: [{ modelProfileId }],
        currency: "USD",
        enabled: true,
        maxConcurrency: 1,
        maxCostMicros: 50_000,
        maxRetries: 1,
        promptProfileId,
        retryPolicy: {
          knowledgeMaxInputUnits: 512,
          maxOutputUnits: 64,
          requireReportedUsage: true,
          temperature: 0
        },
        timeoutMs: 5_000
      },
      expectedRevision: 0,
      idempotencyKey: `e2e-route-${capabilityKey}-revision-1`,
      method: "POST"
    }
  );
  expect(created.data).toMatchObject({
    revision: 1,
    status: "draft"
  });
  const validated = await callRuntime<{
    routeRevision: number;
    status: string;
  }>(
    request,
    `/api/v1/system/capability-routes/${capabilityKey}/revisions/1/validate`,
    {
      idempotencyKey: `e2e-route-${capabilityKey}-validate`,
      method: "POST"
    }
  );
  expect(validated.data.status).toBe("valid");
  const active = await callRuntime<{
    activeRevisionId: string | null;
    validationStatus: string;
  }>(
    request,
    `/api/v1/system/capability-routes/${capabilityKey}/revisions/1/activate`,
    {
      expectedRevision: requireRevision(validated.meta.revision),
      idempotencyKey: `e2e-route-${capabilityKey}-activate`,
      method: "POST"
    }
  );
  expect(active.data).toMatchObject({
    activeRevisionId: expect.any(String),
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
    chatCompletionRequests: number;
    evidenceKind: string;
    modelsRequests: number;
    providerEvidenceKind: string;
    reportedUsageResponses: number;
  };
  expect(evidence).toMatchObject({
    evidenceKind: "p0h_controlled_contract",
    providerEvidenceKind: "controlled_contract"
  });
  expect(evidence.authorizedRequests).toBeGreaterThanOrEqual(4);
  expect(evidence.modelsRequests).toBeGreaterThanOrEqual(2);
  expect(evidence.chatCompletionRequests).toBeGreaterThanOrEqual(2);
  expect(evidence.reportedUsageResponses).toBeGreaterThanOrEqual(2);
  expect(JSON.stringify(evidence)).not.toContain(state.providerCredential);
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
