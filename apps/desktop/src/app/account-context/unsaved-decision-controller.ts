import { shallowReactive } from "vue";

import type {
  UnsavedGuardDecision,
  UnsavedGuardDecisionPort,
  UnsavedGuardPrompt
} from "./types";

export type PendingUnsavedDecision = {
  id: number;
  prompt: UnsavedGuardPrompt;
};

type PendingResolver = {
  id: number;
  resolve: (decision: UnsavedGuardDecision) => void;
  removeAbortListener: () => void;
};

export class AccountUnsavedDecisionController
  implements UnsavedGuardDecisionPort {
  readonly state = shallowReactive<{
    pending: PendingUnsavedDecision | null;
  }>({
    pending: null
  });

  private sequence = 0;
  private resolver: PendingResolver | null = null;

  decide(prompt: UnsavedGuardPrompt): Promise<UnsavedGuardDecision> {
    this.resolve("cancel");
    const id = ++this.sequence;
    return new Promise((resolve) => {
      const handleAbort = () => this.resolveById(id, "cancel");
      prompt.signal.addEventListener("abort", handleAbort, { once: true });
      this.resolver = {
        id,
        resolve,
        removeAbortListener: () =>
          prompt.signal.removeEventListener("abort", handleAbort)
      };
      this.state.pending = { id, prompt };
    });
  }

  resolve(decision: UnsavedGuardDecision): void {
    const pending = this.resolver;
    if (!pending) return;
    this.resolveById(pending.id, decision);
  }

  private resolveById(
    id: number,
    decision: UnsavedGuardDecision
  ): void {
    const pending = this.resolver;
    if (!pending || pending.id !== id) return;
    this.resolver = null;
    this.state.pending = null;
    pending.removeAbortListener();
    pending.resolve(decision);
  }
}
