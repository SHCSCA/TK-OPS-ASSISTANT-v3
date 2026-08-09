<template>
  <Teleport to="body">
    <div
      v-if="pending"
      class="account-unsaved-backdrop"
      @mousedown.self="submitDecision('cancel')"
    >
      <section
        ref="dialogRef"
        class="account-unsaved-dialog"
        role="dialog"
        aria-modal="true"
        :aria-busy="Boolean(submittingDecision)"
        aria-labelledby="account-unsaved-title"
        @keydown="handleKeydown"
      >
        <span class="material-symbols-outlined account-unsaved-dialog__icon">
          edit_note
        </span>
        <h2 id="account-unsaved-title">仍有未保存内容</h2>
        <p>继续后会切换当前账号工作区。</p>
        <ul>
          <li v-for="guard in pending.prompt.guards" :key="guard.id">
            {{ guard.label }}
          </li>
        </ul>
        <div class="account-unsaved-dialog__actions">
          <button
            ref="cancelButtonRef"
            type="button"
            :disabled="Boolean(submittingDecision)"
            @click="submitDecision('cancel')"
          >
            取消
          </button>
          <button
            type="button"
            :disabled="Boolean(submittingDecision)"
            @click="submitDecision('discard')"
          >
            {{ submittingDecision === "discard" ? "正在放弃…" : "放弃并继续" }}
          </button>
          <button
            class="account-unsaved-dialog__primary"
            type="button"
            :disabled="Boolean(submittingDecision)"
            @click="submitDecision('save')"
          >
            {{ submittingDecision === "save" ? "正在保存…" : "保存并继续" }}
          </button>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from "vue";

import type {
  PendingUnsavedDecision
} from "@/app/account-context/unsaved-decision-controller";
import type { UnsavedGuardDecision } from "@/app/account-context";

const props = defineProps<{
  pending: PendingUnsavedDecision | null;
}>();

const emit = defineEmits<{
  decide: [decision: UnsavedGuardDecision];
}>();

const dialogRef = ref<HTMLElement | null>(null);
const cancelButtonRef = ref<HTMLButtonElement | null>(null);
const submittingDecision = ref<UnsavedGuardDecision | null>(null);

watch(
  () => props.pending?.id ?? null,
  async (pending) => {
    submittingDecision.value = null;
    if (!pending) return;
    await nextTick();
    cancelButtonRef.value?.focus();
  }
);

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    event.preventDefault();
    submitDecision("cancel");
    return;
  }
  if (event.key !== "Tab" || !dialogRef.value) return;
  const focusable = Array.from(
    dialogRef.value.querySelectorAll<HTMLButtonElement>(
      "button:not(:disabled)"
    )
  );
  if (focusable.length === 0) return;
  const currentIndex = focusable.indexOf(
    document.activeElement as HTMLButtonElement
  );
  const nextIndex = event.shiftKey
    ? currentIndex <= 0
      ? focusable.length - 1
      : currentIndex - 1
    : currentIndex >= focusable.length - 1
      ? 0
      : currentIndex + 1;
  event.preventDefault();
  focusable[nextIndex]?.focus();
}

function submitDecision(decision: UnsavedGuardDecision): void {
  if (submittingDecision.value) return;
  submittingDecision.value = decision;
  emit("decide", decision);
}
</script>
