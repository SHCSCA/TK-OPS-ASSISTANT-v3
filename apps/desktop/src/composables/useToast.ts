import { reactive, readonly } from "vue";

export type ToastTone = "info" | "success" | "warning" | "danger";

export interface ToastItem {
  id: number;
  title: string;
  message: string;
  tone: ToastTone;
  durationMs: number;
}

interface ToastState {
  items: ToastItem[];
}

const state = reactive<ToastState>({ items: [] });
let nextId = 1;

function push(title: string, message: string, tone: ToastTone, durationMs = 4000): void {
  const id = nextId++;
  state.items.push({ id, title, message, tone, durationMs });
  if (durationMs > 0) {
    setTimeout(() => dismiss(id), durationMs);
  }
}

function dismiss(id: number): void {
  const index = state.items.findIndex((item) => item.id === id);
  if (index !== -1) {
    state.items.splice(index, 1);
  }
}

export function useToast() {
  return {
    items: readonly(state).items,
    dismiss,
    info: (title: string, message = "") => push(title, message, "info"),
    success: (title: string, message = "") => push(title, message, "success"),
    warning: (title: string, message = "") => push(title, message, "warning"),
    danger: (title: string, message = "") => push(title, message, "danger"),
  };
}
