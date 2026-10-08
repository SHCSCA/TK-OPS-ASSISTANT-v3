import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AIExecutionDetailPanel from "@/modules/ai-executions/components/AIExecutionDetailPanel.vue";
import AIExecutionLauncher from "@/modules/ai-executions/components/AIExecutionLauncher.vue";
import AIExecutionStatePanel from "@/modules/ai-executions/components/AIExecutionStatePanel.vue";
import { useAIExecutionStore } from "@/modules/ai-executions/ai-execution-store";
import type {
  AIExecutionAcceptedDto,
  AIExecutionDetailDto,
  AIExecutionSummaryDto
} from "@/types/runtime/ai-executions";

const executionApi = vi.hoisted(() => ({
  cancelAIExecution: vi.fn(),
  createAIExecution: vi.fn(),
  getAIExecution: vi.fn(),
  getAIExecutionOutput: vi.fn(),
  listAIExecutions: vi.fn(),
  preflightAIExecution: vi.fn(),
  retryAIExecution: vi.fn()
}));
const knowledgeApi = vi.hoisted(() => ({
  listAccountKnowledgeSnapshots: vi.fn()
}));

vi.mock("@/app/runtime-client/ai-executions", () => executionApi);
vi.mock("@/app/runtime-client/account-knowledge", () => knowledgeApi);

describe("P0-H AI Execution 桌面交互", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    executionApi.listAIExecutions.mockResolvedValue(runtimeResult({
      items: [],
      totalKnown: 0
    }));
    knowledgeApi.listAccountKnowledgeSnapshots.mockResolvedValue(runtimeResult({
      items: [knowledgeSnapshot("account-1")],
      totalKnown: 1
    }));
  });

  it("覆盖 loading、空态、错误态和远端终态未知的计费提示", async () => {
    const state = mount(AIExecutionStatePanel, {
      props: {
        state: "loading",
        items: [],
        selectedId: null
      }
    });
    expect(state.text()).toContain("正在读取");
    await state.setProps({ state: "first_use" });
    expect(state.text()).toContain("尚无真实执行记录");
    await state.setProps({ state: "error", errorMessage: "Runtime 暂不可用" });
    expect(state.text()).toContain("Runtime 暂不可用");

    const detail = mount(AIExecutionDetailPanel, {
      props: {
        detail: executionDetail({
          status: "failed",
          failureKind: "result_unknown",
          costMicros: null,
          costStatus: "unavailable",
          availableActions: ["retry_same_snapshot"]
        }),
        outputContent: null,
        busy: false
      }
    });
    expect(detail.text()).toContain("远端终态未知");
    expect(detail.text()).toContain("可能已产生调用与费用");
    expect(detail.text()).toContain("费用待确认");
    await detail.get("button.ai-execution-button.is-primary").trigger("click");
    expect(detail.emitted("retry")?.[0]).toEqual(["execution-1"]);
  });

  it("取消终态显示为已取消，不伪装成普通完成", () => {
    const detail = mount(AIExecutionDetailPanel, {
      props: {
        detail: executionDetail({
          status: "completed",
          completionKind: "cancelled",
          failureKind: null,
          costStatus: "unavailable"
        }),
        outputContent: null,
        busy: false
      }
    });
    expect(detail.get("h4").text()).toBe("已取消");
    expect(detail.text()).toContain("费用待确认");
  });

  it("预检阻断项展示具体原因并提供 RepairAction", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const store = useAIExecutionStore();
    const cache = store.cache("account-1");
    cache.state = "ready";
    cache.preflight = {
      accountId: "account-1",
      capabilityKey: "script_generation",
      ready: false,
      candidateCount: 0,
      blockingIssues: [{
        code: "AI_PROVIDER_REAL_VALIDATION_REQUIRED",
        severity: "error",
        nodeType: "model_profile_revision",
        nodeId: "model-revision-1",
        path: "candidates[0]",
        message: "候选模型尚未通过当前修订的真实小调用",
        blocking: true,
        evidenceRef: null
      }],
      repairActions: [{
        kind: "navigate",
        label: "前往验证模型",
        targetPage: "ai-system-settings",
        targetSection: "providers",
        targetResourceId: "model-1",
        requiredAccountId: null
      }],
      costEstimate: {
        currency: "USD",
        minimumMicros: null,
        maximumMicros: null,
        budgetLimitMicros: 50_000
      },
      snapshotPreviewHash: "d".repeat(64)
    };
    vi.spyOn(store, "load").mockResolvedValue(undefined);

    const wrapper = mount(AIExecutionLauncher, {
      global: { plugins: [pinia] },
      props: {
        accountId: "account-1",
        accountRevision: 3,
        recipeVersionId: "recipe-version-1"
      }
    });
    expect(wrapper.text()).toContain("候选模型尚未通过当前修订的真实小调用");
    const repair = wrapper.findAll("button").find(
      (item) => item.text().trim() === "前往验证模型"
    );
    if (!repair) throw new Error("未找到修复动作");
    await repair.trigger("click");
    expect(wrapper.emitted("repair")?.[0]?.[0]).toMatchObject({
      targetSection: "providers"
    });
  });

  it("预检只提交用户可控预算，超时与重试继承 Route 和配置总线", async () => {
    const store = useAIExecutionStore();
    const cache = store.cache("account-1");
    cache.topic = "验证 Route 继承策略";
    cache.selectedKnowledgeSnapshotId = "snapshot-account-1";
    executionApi.preflightAIExecution.mockResolvedValue(runtimeResult({
      accountId: "account-1",
      capabilityKey: "script_generation",
      ready: true,
      candidateCount: 1,
      blockingIssues: [],
      repairActions: [],
      costEstimate: {
        currency: "USD",
        minimumMicros: 10,
        maximumMicros: 20,
        budgetLimitMicros: 50_000
      },
      snapshotPreviewHash: "e".repeat(64)
    }));

    expect(await store.runPreflight("account-1", 3, "recipe-version-1"))
      .toBe(true);
    expect(executionApi.preflightAIExecution).toHaveBeenCalledWith(
      "account-1",
      expect.objectContaining({
        executionPolicy: {
          currency: "USD",
          maxCostMicros: 50_000
        }
      }),
      expect.objectContaining({
        expectedRevision: 3,
        signal: expect.any(AbortSignal)
      })
    );
    const submitted = executionApi.preflightAIExecution.mock.calls[0]?.[1]
      .executionPolicy;
    expect(submitted).not.toHaveProperty("timeoutMs");
    expect(submitted).not.toHaveProperty("maxRetries");
    expect(submitted).not.toHaveProperty("allowFallback");
  });

  it("cancel 和 same_snapshot retry 走 Runtime 并保留可见反馈", async () => {
    const store = useAIExecutionStore();
    store.activateAccount("account-1");
    executionApi.cancelAIExecution.mockResolvedValue(runtimeResult(
      executionDetail({
        status: "completed",
        completionKind: "cancelled",
        failureKind: null
      })
    ));
    executionApi.retryAIExecution.mockResolvedValue(runtimeResult(
      executionAccepted("execution-retry-1")
    ));
    vi.spyOn(store, "load").mockResolvedValue(undefined);

    expect(await store.cancel("account-1", "execution-1")).toBe(true);
    expect(executionApi.cancelAIExecution).toHaveBeenCalledWith(
      "account-1",
      "execution-1",
      expect.objectContaining({ idempotencyKey: expect.any(String) })
    );
    expect(store.cache("account-1").feedback).toContain("费用仍以详情证据为准");

    expect(await store.retry("account-1", "execution-1")).toBe(true);
    expect(executionApi.retryAIExecution).toHaveBeenCalledWith(
      "account-1",
      "execution-1",
      expect.objectContaining({ idempotencyKey: expect.any(String) })
    );
    expect(store.cache("account-1").selectedExecutionId).toBe("execution-retry-1");
  });

  it("账号切换取消旧请求，迟到响应不会污染新账号缓存", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const store = useAIExecutionStore();
    const delayed = deferred<ReturnType<typeof runtimeResult>>();
    executionApi.listAIExecutions.mockImplementation((accountId: string) => {
      if (accountId === "account-a") return delayed.promise;
      return Promise.resolve(runtimeResult({ items: [], totalKnown: 0 }));
    });
    knowledgeApi.listAccountKnowledgeSnapshots.mockImplementation(
      (accountId: string) => Promise.resolve(runtimeResult({
        items: [knowledgeSnapshot(accountId)],
        totalKnown: 1
      }))
    );

    const oldLoad = store.load("account-a");
    await store.load("account-b");
    delayed.resolve(runtimeResult({
      items: [executionSummary("account-a")],
      totalKnown: 1
    }));
    await oldLoad;
    await flushPromises();

    expect(store.visibleAccountId).toBe("account-b");
    expect(store.cache("account-b").executions).toEqual([]);
    expect(store.cache("account-a").executions).toEqual([]);
    expect(Object.keys(store.cacheByAccount)).toEqual(expect.arrayContaining([
      "account:account-a:ai-executions",
      "account:account-b:ai-executions"
    ]));
  });
});

function executionSummary(accountId = "account-1"): AIExecutionSummaryDto {
  return {
    id: "execution-1",
    accountId,
    capabilityKey: "script_generation",
    status: "failed",
    completionKind: null,
    failureKind: "result_unknown",
    taskId: "task-execution-1",
    snapshotHash: "a".repeat(64),
    costMicros: null,
    costStatus: "unavailable",
    outputCount: 0,
    errorCode: "AI_PROVIDER_RESULT_UNKNOWN",
    logId: "log-execution-1",
    revision: 2,
    createdAt: "2026-08-10T10:00:00Z",
    startedAt: "2026-08-10T10:00:01Z",
    completedAt: "2026-08-10T10:00:02Z",
    updatedAt: "2026-08-10T10:00:02Z"
  };
}

function executionDetail(
  overrides: Partial<AIExecutionDetailDto> = {}
): AIExecutionDetailDto {
  return {
    ...executionSummary(),
    retryOfExecutionId: null,
    progress: 1,
    cancellable: false,
    snapshot: { aiConfigRevision: 8 },
    candidates: [],
    jobs: [],
    usage: [],
    outputs: [],
    errors: [{
      errorCode: "AI_PROVIDER_RESULT_UNKNOWN",
      stage: "provider_execute",
      retryable: false,
      safeSummary: "远端结果无法确认",
      logId: "log-execution-1"
    }],
    availableActions: ["retry_same_snapshot"],
    ...overrides
  };
}

function executionAccepted(executionId: string): AIExecutionAcceptedDto {
  return {
    executionId,
    taskId: `task-${executionId}`,
    accountId: "account-1",
    capabilityKey: "script_generation",
    status: "queued",
    snapshotHash: "a".repeat(64),
    revision: 1,
    createdAt: "2026-08-10T10:05:00Z"
  };
}

function knowledgeSnapshot(accountId: string) {
  return {
    id: `snapshot-${accountId}`,
    accountId,
    label: "当前知识快照",
    sourceIds: ["source-1"],
    sourceEvidence: [{
      sourceId: "source-1",
      contentHash: "b".repeat(64),
      indexedRevision: 1
    }],
    rulesVersion: 1,
    contentHash: "c".repeat(64),
    createdAt: "2026-08-10T09:00:00Z"
  };
}

function runtimeResult<T = unknown>(data: T) {
  return {
    data,
    meta: null,
    operationId: null,
    requestId: "request-p0-h-execution",
    status: 200
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
