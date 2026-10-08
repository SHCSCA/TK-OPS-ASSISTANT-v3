import { expect, type APIRequestContext } from "@playwright/test";

import {
  callRuntime,
  waitForRuntimeTask
} from "./runtime-api";
import { readE2eRuntimeState } from "./runtime-state";

type AccountDto = {
  id: string;
  name: string;
  revision: number;
};

type ProviderDto = {
  credentialSummary: { configured: boolean; maskedValue: string | null };
  healthStatus: string;
  id: string;
  revision: number;
};

type ModelDto = {
  capabilities: Array<{
    availability: string;
    capabilityKey: string;
    contractVerified: boolean;
  }>;
  id: string;
  modelId: string;
  revision: number;
};

type PromptProfileDto = {
  activeVersion: number | null;
  activeVersionId: string | null;
  profileKey: string;
  revision: number;
};

type TaskAcceptedDto = { taskId: string };

export type P0HRuntimeChain = {
  accountId: string;
  accountName: string;
  accountRevision: number;
  isolationAccountId: string;
  knowledgeSnapshotId: string;
  modelProfileId: string;
  promptVersionId: string;
  providerProfileId: string;
  recipeVersionId: string;
};

export async function prepareP0HRuntimeChain(
  request: APIRequestContext
): Promise<P0HRuntimeChain> {
  await enableAIExecution(request);
  const state = readE2eRuntimeState();
  const account = await createAccount(
    request,
    "P0-H 真实 AI 验证账号",
    "p0h_real_ai",
    "primary"
  );
  const isolation = await createAccount(
    request,
    "P0-H 隔离对照账号",
    "p0h_isolation",
    "isolation"
  );
  const provider = await configureProvider(
    request,
    `${state.providerBaseUrl}/v1`,
    state.providerCredential
  );
  const model = await discoverAndValidateModel(request, provider.id);
  const prompt = await createActivePrompt(request);
  await createActiveRoute(request, model.id, prompt.activeVersionId!);
  const knowledgeSnapshotId = await createKnowledgeSnapshot(
    request,
    account.id
  );
  const recipe = await createActiveRecipe(request, account.id);
  const refreshed = await getAccount(request, account.id);
  return {
    accountId: account.id,
    accountName: account.name,
    accountRevision: refreshed.revision,
    isolationAccountId: isolation.id,
    knowledgeSnapshotId,
    modelProfileId: model.id,
    promptVersionId: prompt.activeVersionId!,
    providerProfileId: provider.id,
    recipeVersionId: recipe.id
  };
}

async function enableAIExecution(request: APIRequestContext): Promise<void> {
  const current = await callRuntime<{
    revision: number;
    values: Record<string, unknown>;
  }>(request, "/api/v1/system/config");
  if (current.data.values["ai.execution.enabled"] === true) return;
  const updated = await callRuntime<{
    revision: number;
    values: Record<string, unknown>;
  }>(request, "/api/v1/system/config", {
    data: { values: { "ai.execution.enabled": true } },
    expectedRevision: current.data.revision,
    method: "PATCH"
  });
  expect(updated.data.values["ai.execution.enabled"]).toBe(true);
}

async function createAccount(
  request: APIRequestContext,
  name: string,
  username: string,
  key: string
): Promise<AccountDto> {
  return (
    await callRuntime<AccountDto>(request, "/api/v1/accounts", {
      data: { name, platform: "tiktok", username },
      idempotencyKey: `p0h-account-${key}`,
      method: "POST"
    })
  ).data;
}

async function getAccount(
  request: APIRequestContext,
  accountId: string
): Promise<AccountDto> {
  return (
    await callRuntime<AccountDto>(
      request,
      `/api/v1/accounts/${encodeURIComponent(accountId)}`
    )
  ).data;
}

async function configureProvider(
  request: APIRequestContext,
  baseUrl: string,
  credential: string
): Promise<ProviderDto> {
  const created = await callRuntime<ProviderDto>(
    request,
    "/api/v1/system/providers",
    {
      data: {
        adapterType: "openai_compatible",
        baseUrl,
        costPolicy: {
          inputMicrosPerMillionUnits: 1_000_000,
          outputMicrosPerMillionUnits: 2_000_000,
          pricingRevision: 1
        },
        enabled: true,
        extraParams: { protocolVariant: "chat_completions" },
        maxConcurrency: 1,
        name: "P0-H 受控 OpenAI-compatible Provider",
        region: null,
        timeoutMs: 5_000
      },
      idempotencyKey: "p0h-provider-controlled",
      method: "POST"
    }
  );
  const credentialResult = await callRuntime<{
    configured: true;
    maskedValue: string;
    providerRevision: number;
  }>(request, `/api/v1/system/providers/${created.data.id}/credential`, {
    data: { credential },
    expectedRevision: created.data.revision,
    method: "PUT"
  });
  expect(credentialResult.data.configured).toBe(true);
  expect(JSON.stringify(credentialResult)).not.toContain(credential);

  const latest = await getProvider(request, created.data.id);
  const check = await callRuntime<TaskAcceptedDto>(
    request,
    `/api/v1/system/providers/${latest.id}/checks`,
    {
      data: {
        force: true,
        stages: ["network", "authentication"]
      },
      idempotencyKey: "p0h-provider-health",
      method: "POST"
    }
  );
  await waitForRuntimeTask(request, check.data.taskId);
  const ready = await getProvider(request, latest.id);
  expect(ready).toMatchObject({
    credentialSummary: { configured: true },
    healthStatus: "ready"
  });
  return ready;
}

async function getProvider(
  request: APIRequestContext,
  providerId: string
): Promise<ProviderDto> {
  return (
    await callRuntime<ProviderDto>(
      request,
      `/api/v1/system/providers/${encodeURIComponent(providerId)}`
    )
  ).data;
}

async function discoverAndValidateModel(
  request: APIRequestContext,
  providerId: string
): Promise<ModelDto> {
  const discovery = await callRuntime<TaskAcceptedDto>(
    request,
    `/api/v1/system/providers/${providerId}/model-discovery`,
    {
      data: { replaceMissing: false },
      idempotencyKey: "p0h-provider-model-discovery",
      method: "POST"
    }
  );
  await waitForRuntimeTask(request, discovery.data.taskId);
  const page = await callRuntime<{ items: ModelDto[] }>(
    request,
    `/api/v1/system/models?providerId=${encodeURIComponent(providerId)}&limit=100`
  );
  const discovered = page.data.items.find(
    (item) => item.modelId === "tk-e2e-text-1"
  );
  if (!discovered) throw new Error("真实模型发现未返回受控文本模型。");
  const enabled = await callRuntime<ModelDto>(
    request,
    `/api/v1/system/models/${discovered.id}`,
    {
      data: { enabled: true },
      expectedRevision: discovered.revision,
      method: "PATCH"
    }
  );
  const check = await callRuntime<TaskAcceptedDto>(
    request,
    `/api/v1/system/models/${enabled.data.id}/capability-checks`,
    {
      data: {
        capabilityKeys: ["script_generation"],
        force: true,
        mode: "real_small_call"
      },
      idempotencyKey: "p0h-model-real-small-call",
      method: "POST"
    }
  );
  await waitForRuntimeTask(request, check.data.taskId);
  const verified = (
    await callRuntime<ModelDto>(
      request,
      `/api/v1/system/models/${enabled.data.id}`
    )
  ).data;
  expect(verified.capabilities).toContainEqual(expect.objectContaining({
    availability: "available",
    capabilityKey: "script_generation",
    contractVerified: true
  }));
  return verified;
}

async function createActivePrompt(
  request: APIRequestContext
): Promise<PromptProfileDto> {
  const profileKey = "p0h-script-generation";
  const created = await callRuntime<PromptProfileDto>(
    request,
    "/api/v1/system/prompt-profiles",
    {
      data: {
        capabilityKey: "script_generation",
        name: "P0-H 真实脚本生成 Prompt",
        outputSchema: {
          properties: { script: { type: "string" } },
          required: ["script"],
          type: "object"
        },
        profileKey,
        safetyConstraints: { avoidUnsupportedClaims: true },
        systemPrompt: "你是账号定位驱动的短视频脚本助手，只输出 JSON。",
        taskTemplate: "围绕主题 {{topic}} 生成结构清晰的短视频脚本。",
        variablesSchema: {
          properties: {
            language: { type: "string" },
            targetDurationSeconds: { type: "integer" },
            topic: { type: "string" }
          },
          required: ["topic"],
          type: "object"
        },
        visualStylePrefix: ""
      },
      idempotencyKey: "p0h-prompt-create",
      method: "POST"
    }
  );
  const activated = await callRuntime<PromptProfileDto>(
    request,
    `/api/v1/system/prompt-profiles/${profileKey}/versions/1/activate`,
    {
      expectedRevision: created.data.revision,
      idempotencyKey: "p0h-prompt-activate",
      method: "POST"
    }
  );
  expect(activated.data.activeVersionId).toBeTruthy();
  return activated.data;
}

async function createActiveRoute(
  request: APIRequestContext,
  modelProfileId: string,
  promptVersionId: string
): Promise<void> {
  const created = await callRuntime<{ revision: number; status: string }>(
    request,
    "/api/v1/system/capability-routes/script_generation/revisions",
    {
      data: {
        candidates: [{ modelProfileId }],
        currency: "USD",
        enabled: true,
        maxConcurrency: 1,
        maxCostMicros: 50_000,
        maxRetries: 1,
        promptProfileId: promptVersionId,
        retryPolicy: {
          knowledgeMaxInputUnits: 512,
          maxOutputUnits: 64,
          requireReportedUsage: true,
          temperature: 0
        },
        timeoutMs: 5_000
      },
      expectedRevision: 0,
      idempotencyKey: "p0h-route-create",
      method: "POST"
    }
  );
  expect(created.data).toMatchObject({ revision: 1, status: "draft" });
  const validated = await callRuntime<{
    routeRevision: number;
    status: string;
  }>(
    request,
    "/api/v1/system/capability-routes/script_generation/revisions/1/validate",
    {
      idempotencyKey: "p0h-route-validate",
      method: "POST"
    }
  );
  expect(validated.data.status).toBe("valid");
  const revision = validated.meta.revision;
  if (!Number.isInteger(revision)) {
    throw new Error("能力路由验证未返回聚合修订号。");
  }
  const active = await callRuntime<{
    activeRevisionId: string | null;
    validationStatus: string;
  }>(
    request,
    "/api/v1/system/capability-routes/script_generation/revisions/1/activate",
    {
      expectedRevision: revision,
      idempotencyKey: "p0h-route-activate",
      method: "POST"
    }
  );
  expect(active.data).toMatchObject({
    activeRevisionId: expect.any(String),
    validationStatus: "valid"
  });
}

async function createKnowledgeSnapshot(
  request: APIRequestContext,
  accountId: string
): Promise<string> {
  const source = await callRuntime<{ id: string }>(
    request,
    `/api/v1/accounts/${accountId}/knowledge/sources`,
    {
      data: {
        kind: "text",
        sourceMode: "text",
        text: "该账号服务短视频创作者，表达直接、克制、有证据，避免夸张承诺。",
        title: "P0-H 受控账号知识"
      },
      idempotencyKey: "p0h-knowledge-source",
      method: "POST"
    }
  );
  const index = await callRuntime<TaskAcceptedDto>(
    request,
    `/api/v1/accounts/${accountId}/knowledge/index-jobs`,
    {
      data: { sourceIds: [source.data.id] },
      idempotencyKey: "p0h-knowledge-index",
      method: "POST"
    }
  );
  await waitForRuntimeTask(request, index.data.taskId, accountId);
  const snapshot = await callRuntime<{ id: string }>(
    request,
    `/api/v1/accounts/${accountId}/knowledge/snapshots`,
    {
      data: {
        label: "P0-H 真实执行知识快照",
        sourceIds: [source.data.id]
      },
      idempotencyKey: "p0h-knowledge-snapshot",
      method: "POST"
    }
  );
  return snapshot.data.id;
}

async function createActiveRecipe(
  request: APIRequestContext,
  accountId: string
): Promise<{ id: string }> {
  const account = await getAccount(request, accountId);
  const created = await callRuntime<{
    id: string;
    validationStatus: string;
    version: number;
  }>(request, `/api/v1/accounts/${accountId}/ai-recipe/versions`, {
    data: {
      compositionTemplateRef: null,
      costPolicy: {},
      fallbackPolicy: {},
      name: "P0-H 真实执行 Recipe",
      routeOverrides: {},
      visualStyle: {},
      voiceProfileRef: null
    },
    expectedRevision: account.revision,
    idempotencyKey: "p0h-recipe-create",
    method: "POST"
  });
  const validated = await callRuntime<{
    resolvedRouteSummary: Record<string, { source: string }>;
    validationStatus: string;
  }>(
    request,
    `/api/v1/accounts/${accountId}/ai-recipe/versions/1/validate`,
    {
      idempotencyKey: "p0h-recipe-validate",
      method: "POST"
    }
  );
  expect(validated.data.validationStatus).toBe("valid");
  expect(validated.data.resolvedRouteSummary.script_generation?.source)
    .toBe("system");
  const revision = validated.meta.revision;
  if (!Number.isInteger(revision)) {
    throw new Error("账号 Recipe 验证未返回账号修订号。");
  }
  const activated = await callRuntime<{
    activeVersion: number | null;
    activeVersionId: string | null;
  }>(
    request,
    `/api/v1/accounts/${accountId}/ai-recipe/versions/1/activate`,
    {
      expectedRevision: revision,
      idempotencyKey: "p0h-recipe-activate",
      method: "POST"
    }
  );
  expect(activated.data).toMatchObject({
    activeVersion: 1,
    activeVersionId: created.data.id
  });
  return created.data;
}
