import { reactive, ref, watch } from "vue";
import { useConfigBusStore } from "@/stores/config-bus";
import type { AppSettingsUpdateInput } from "@/types/runtime";

/**
 * 系统设置：目录、缓存、日志、字幕等表单管理
 */
export function useSystemSettings() {
  const configBusStore = useConfigBusStore();

  const systemForm = reactive<AppSettingsUpdateInput>({
    runtime: { mode: "local", workspaceRoot: "" },
    paths: { cacheDir: "", exportDir: "", logDir: "" },
    logging: { level: "INFO" },
    ai: { provider: "openai", model: "gpt-4o", voice: "alloy", subtitleMode: "balanced" }
  });
  const systemDirty = ref(false);

  watch(() => configBusStore.settings, (s) => {
    if (s) {
      systemForm.runtime = { ...s.runtime };
      systemForm.paths = { ...s.paths };
      systemForm.logging = { ...s.logging };
      systemForm.ai = { ...s.ai };
      systemDirty.value = false;
    }
  }, { immediate: true });

  function updateSystemForm(patch: Partial<AppSettingsUpdateInput>) {
    if (patch.logging) Object.assign(systemForm.logging, patch.logging);
    if (patch.ai) Object.assign(systemForm.ai, patch.ai);
    if (patch.runtime) Object.assign(systemForm.runtime, patch.runtime);
    if (patch.paths) Object.assign(systemForm.paths, patch.paths);
    systemDirty.value = true;
  }

  async function handlePickDirectory(field: string) {
    try {
      const dialogModuleName = "@tauri-apps/plugin-dialog";
      const dialog = await import(/* @vite-ignore */ dialogModuleName);
      const selected = await dialog.open({ directory: true, multiple: false });
      if (typeof selected === "string" && selected) {
        const [parent, child] = field.split(".");
        (systemForm as any)[parent][child] = selected;
        systemDirty.value = true;
      }
    } catch {
      const current = field.split(".").reduce((obj: any, key: string) => obj?.[key], systemForm) as string;
      const path = window.prompt("请输入本地目录路径", current);
      if (path !== null && path.trim() !== "") {
        const [parent, child] = field.split(".");
        (systemForm as any)[parent][child] = path.trim();
        systemDirty.value = true;
      }
    }
  }

  async function saveSystemSettings() {
    await configBusStore.save(systemForm);
    systemDirty.value = false;
  }

  return {
    systemForm,
    systemDirty,
    updateSystemForm,
    handlePickDirectory,
    saveSystemSettings
  };
}
