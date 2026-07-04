import { confirm } from "@tauri-apps/plugin-dialog";
import { afterEach, describe, expect, it, vi } from "vitest";

import { requestDesktopConfirm } from "../src/composables/useDesktopConfirm";

vi.mock("@tauri-apps/plugin-dialog", () => ({
  confirm: vi.fn()
}));

describe("desktop confirm helper", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("优先使用 Tauri 桌面对话框", async () => {
    vi.mocked(confirm).mockResolvedValue(true);

    await expect(requestDesktopConfirm("时间线有未保存的更改，确定要离开吗？", { title: "离开工作台" })).resolves.toBe(true);

    expect(confirm).toHaveBeenCalledWith("时间线有未保存的更改，确定要离开吗？", {
      title: "离开工作台",
      kind: "warning"
    });
  });

  it("桌面对话框不可用时回退到注入的确认函数并记录中文诊断", async () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    vi.mocked(confirm).mockRejectedValue(new Error("dialog unavailable"));

    await expect(
      requestDesktopConfirm("时间线有未保存的更改，确定要离开吗？", {
        title: "离开工作台",
        fallbackConfirm: () => false
      })
    ).resolves.toBe(false);

    expect(warnSpy).toHaveBeenCalledWith("桌面确认对话框不可用，已回退到浏览器确认。", expect.any(Error));
  });
});
