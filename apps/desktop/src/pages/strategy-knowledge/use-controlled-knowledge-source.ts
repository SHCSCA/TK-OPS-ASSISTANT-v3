import { ref } from "vue";

import {
  pickAccountControlledFile
} from "@/app/controlled-files/client";
import {
  ControlledFileBridgeError,
  type AccountControlledFile
} from "@/app/controlled-files/types";
import { listExecutionEnvironments } from "@/app/runtime-client/execution-environments";

type ControlledKnowledgeSourceCallbacks = {
  onError: (accountId: string, error: unknown) => void;
  onSelected: (accountId: string, file: AccountControlledFile) => void;
};

export function useControlledKnowledgeSource(
  callbacks: ControlledKnowledgeSourceCallbacks
) {
  const selecting = ref(false);
  let sequence = 0;

  async function select(accountId: string): Promise<void> {
    const current = ++sequence;
    selecting.value = true;
    try {
      const result = await listExecutionEnvironments(accountId);
      const environment = result.data.items.find(
        (item) => item.status === "active" && item.workspace.status === "active"
      );
      if (!environment) {
        throw new ControlledFileBridgeError(
          "当前账号没有可用工作目录，请先在账号管理中建立执行环境。",
          { errorCode: "CONTROLLED_FILE_WORKSPACE_REQUIRED" }
        );
      }
      const file = await pickAccountControlledFile(
        accountId,
        environment.workspace.rootRef
      );
      if (current === sequence && file) callbacks.onSelected(accountId, file);
    } catch (error) {
      if (current === sequence) callbacks.onError(accountId, error);
    } finally {
      if (current === sequence) selecting.value = false;
    }
  }

  function stop(): void {
    sequence += 1;
    selecting.value = false;
  }

  return { select, selecting, stop };
}
