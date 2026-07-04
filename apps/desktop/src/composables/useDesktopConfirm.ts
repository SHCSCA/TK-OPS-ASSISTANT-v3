import { confirm } from "@tauri-apps/plugin-dialog";

type DesktopConfirmKind = "info" | "warning" | "error";

type DesktopConfirmOptions = {
  fallbackConfirm?: (message: string) => boolean;
  kind?: DesktopConfirmKind;
  title: string;
};

export async function requestDesktopConfirm(message: string, options: DesktopConfirmOptions): Promise<boolean> {
  try {
    return await confirm(message, {
      title: options.title,
      kind: options.kind ?? "warning"
    });
  } catch (error) {
    console.warn("桌面确认对话框不可用，已回退到浏览器确认。", error);
    if (options.fallbackConfirm) {
      return options.fallbackConfirm(message);
    }
    if (typeof window !== "undefined" && typeof window.confirm === "function") {
      return window.confirm(message);
    }
    return false;
  }
}
