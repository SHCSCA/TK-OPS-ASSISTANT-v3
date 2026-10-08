import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import KnowledgeSourcesPanel from "@/modules/knowledge/KnowledgeSourcesPanel.vue";
import { createAccountKnowledgeCache } from "@/modules/knowledge/account-knowledge-cache";
import { sourceInputFromCache } from "@/modules/knowledge/account-knowledge-operations";
import { useAccountKnowledgeStore } from "@/modules/knowledge/account-knowledge-store";
import type { KnowledgeSourceDto } from "@/types/runtime/account-knowledge";
import { useControlledKnowledgeSource } from "@/pages/strategy-knowledge/use-controlled-knowledge-source";

const controlledFiles = vi.hoisted(() => ({
  pickAccountControlledFile: vi.fn()
}));
const environments = vi.hoisted(() => ({
  listExecutionEnvironments: vi.fn()
}));

vi.mock("@/app/controlled-files/client", () => controlledFiles);
vi.mock("@/app/runtime-client/execution-environments", () => environments);

describe("P0-H 受控知识文件", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    environments.listExecutionEnvironments.mockResolvedValue(runtimeResult({
      items: [executionEnvironment()]
    }));
    controlledFiles.pickAccountControlledFile.mockResolvedValue({
      displayName: "品牌语气.txt",
      fileRef: `file_ref_${"a".repeat(32)}`,
      kind: "text",
      revision: 1,
      rootRef: `wr_${"b".repeat(32)}`,
      size: 2048,
      status: "active"
    });
  });

  it("只把账号 rootRef 和 fileRef 带入链路，不向 Runtime 暴露路径", async () => {
    const onSelected = vi.fn();
    const onError = vi.fn();
    const picker = useControlledKnowledgeSource({ onError, onSelected });

    await picker.select("account-1");

    expect(controlledFiles.pickAccountControlledFile).toHaveBeenCalledWith(
      "account-1",
      `wr_${"b".repeat(32)}`
    );
    expect(onError).not.toHaveBeenCalled();
    expect(onSelected).toHaveBeenCalledWith(
      "account-1",
      expect.objectContaining({ fileRef: `file_ref_${"a".repeat(32)}` })
    );

    const store = useAccountKnowledgeStore();
    store.applyControlledFileSelection("account-1", onSelected.mock.calls[0]![1]);
    const input = sourceInputFromCache(store.cache("account-1"));
    expect(input).toEqual({
      kind: "text",
      sourceMode: "file",
      title: "品牌语气.txt",
      controlledFileRef: `file_ref_${"a".repeat(32)}`
    });
    expect(JSON.stringify(input)).not.toMatch(/[A-Z]:\\|\\Users\\/i);
  });

  it("没有真实工作目录时失败封闭并提供恢复原因", async () => {
    environments.listExecutionEnvironments.mockResolvedValueOnce(runtimeResult({
      items: []
    }));
    const onSelected = vi.fn();
    const onError = vi.fn();
    const picker = useControlledKnowledgeSource({ onError, onSelected });

    await picker.select("account-1");

    expect(onSelected).not.toHaveBeenCalled();
    expect(onError.mock.calls[0]?.[1]).toMatchObject({
      errorCode: "CONTROLLED_FILE_WORKSPACE_REQUIRED"
    });
    expect(controlledFiles.pickAccountControlledFile).not.toHaveBeenCalled();
  });

  it("文件表单展示受控摘要，失败来源可重新选择且保留旧证据", async () => {
    const cache = createAccountKnowledgeCache("account-1");
    cache.sourceEditorOpen = true;
    cache.sourceDraft = {
      ...cache.sourceDraft,
      mode: "file",
      title: "品牌语气",
      controlledFileRef: `file_ref_${"a".repeat(32)}`,
      controlledFileName: "品牌语气.txt",
      controlledFileKind: "text",
      controlledFileSize: 2048
    };
    cache.sources = [failedFileSource()];
    cache.sourceState = "ready";
    const wrapper = mount(KnowledgeSourcesPanel, { props: { cache } });

    expect(wrapper.text()).toContain("品牌语气.txt");
    expect(wrapper.text()).toContain("2.0 KB");
    expect(wrapper.text()).not.toContain("C:\\");
    await wrapper.findAll("button").find(
      (item) => item.text().trim() === "重新选择"
    )?.trigger("click");
    expect(wrapper.emitted("recover-file")?.[0]?.[0]).toMatchObject({
      id: "source-file-1"
    });

    const store = useAccountKnowledgeStore();
    store.prepareControlledFileRecovery("account-1", failedFileSource());
    expect(store.cache("account-1").feedback).toContain("旧来源和历史快照会保留");
    expect(store.cache("account-1").sourceDraft.controlledFileRef).toBe("");
  });
});

function failedFileSource(): KnowledgeSourceDto {
  return {
    id: "source-file-1",
    accountId: "account-1",
    kind: "text",
    sourceMode: "file",
    title: "品牌语气",
    status: "stale",
    controlledRef: `file_ref_${"a".repeat(32)}`,
    sourceUrl: null,
    contentHash: "c".repeat(64),
    indexedAt: "2026-08-10T10:00:00Z",
    removedAt: null,
    errorCode: "CONTROLLED_FILE_CHANGED",
    logId: "log-file-1",
    revision: 2,
    asset: {
      id: "asset-file-1",
      status: "stale",
      displayName: "品牌语气.txt",
      kind: "text",
      mediaType: "text/plain",
      byteSize: 2048,
      rootRef: `wr_${"b".repeat(32)}`,
      revision: 2
    }
  };
}

function executionEnvironment() {
  return {
    id: "environment-1",
    accountId: "account-1",
    name: "主执行环境",
    status: "active",
    workspace: {
      id: "workspace-1",
      rootRef: `wr_${"b".repeat(32)}`,
      displayName: "账号工作目录",
      status: "active",
      ownershipState: "owned"
    },
    browser: {
      id: "browser-1",
      kind: "chrome",
      displayName: "Chrome",
      status: "ready",
      ownershipVerified: true,
      lastCheckedAt: "2026-08-10T10:00:00Z"
    },
    eligibility: {
      eligible: true,
      blockingIssues: [],
      checkedAt: "2026-08-10T10:00:00Z",
      evidenceRevision: 1
    },
    revision: 1,
    errorCode: null,
    errorLogId: null,
    errorMessage: null,
    lastTaskId: null,
    lastRetryOfTaskId: null,
    recoveryActions: []
  };
}

function runtimeResult<T>(data: T) {
  return {
    data,
    meta: null,
    operationId: null,
    requestId: "request-p0-h-file",
    status: 200
  };
}
