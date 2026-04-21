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

  type SettingsPath = "runtime.workspaceRoot" | "paths.cacheDir" | "paths.exportDir" | "paths.logDir";

  async function handlePickDirectory(field: SettingsPath) {
    let selected: string | null = null;
    try {
      const dialogModuleName = "@tauri-apps/plugin-dialog";
      const dialog = await import(/* @vite-ignore */ dialogModuleName);
      const result = await dialog.open({ directory: true, multiple: false });
      if (typeof result === "string") selected = result;
    } catch {
      const [parent, child] = field.split(".") as ["runtime" | "paths", string];
      const current = (systemForm[parent] as Record<string, string>)[child];
      selected = window.prompt("请输入本地目录路径", current);
    }

    if (selected && selected.trim() !== "") {
      const [parent, child] = field.split(".") as ["runtime" | "paths", string];
      (systemForm[parent] as Record<string, string>)[child] = selected.trim();
      systemDirty.value = true;
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
