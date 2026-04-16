import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

describe("Tauri capability 权限", () => {
  it("主窗口允许打开系统文件选择器", () => {
    const capabilityPath = resolve(process.cwd(), "src-tauri", "capabilities", "default.json");
    const capability = JSON.parse(readFileSync(capabilityPath, "utf8")) as {
      permissions?: string[];
    };

    expect(capability.permissions).toContain("dialog:allow-open");
  });

  it("允许资产预览通过 Tauri asset 协议读取用户本地素材", () => {
    const configPath = resolve(process.cwd(), "src-tauri", "tauri.conf.json");
    const config = JSON.parse(readFileSync(configPath, "utf8")) as {
      app?: {
        security?: {
          assetProtocol?: {
            enable?: boolean;
            scope?: string[];
          };
        };
      };
    };

    const assetProtocol = config.app?.security?.assetProtocol;

    expect(assetProtocol?.enable).toBe(true);
    expect(assetProtocol?.scope).toEqual(
      expect.arrayContaining(["$HOME/**", "$PICTURE/**", "$VIDEO/**", "$DOCUMENT/**"])
    );
  });
});
