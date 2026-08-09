import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

describe("Tauri capability 权限", () => {
  it("主窗口默认保持宽屏体验，同时允许 960 宽度紧凑窗口验证", () => {
    const configPath = resolve(process.cwd(), "src-tauri", "tauri.conf.json");
    const config = JSON.parse(readFileSync(configPath, "utf8")) as {
      app?: {
        windows?: Array<{
          label?: string;
          width?: number;
          height?: number;
          minWidth?: number;
          minHeight?: number;
          resizable?: boolean;
          maximizable?: boolean;
          minimizable?: boolean;
          closable?: boolean;
          decorations?: boolean;
        }>;
      };
    };

    const mainWindow = config.app?.windows?.find((windowConfig) => windowConfig.label === "main");

    expect(mainWindow?.width).toBe(1680);
    expect(mainWindow?.height).toBe(960);
    expect(mainWindow?.minWidth).toBeLessThanOrEqual(960);
    expect(mainWindow?.minHeight).toBeLessThanOrEqual(720);
    expect(mainWindow?.resizable).toBe(true);
    expect(mainWindow?.maximizable).toBe(true);
    expect(mainWindow?.minimizable).toBe(true);
    expect(mainWindow?.closable).toBe(true);
    expect(mainWindow?.decorations).toBe(true);
  });

  it("主窗口允许打开系统文件选择器", () => {
    const capabilityPath = resolve(process.cwd(), "src-tauri", "capabilities", "default.json");
    const capability = JSON.parse(readFileSync(capabilityPath, "utf8")) as {
      permissions?: string[];
    };

    expect(capability.permissions).toContain("dialog:allow-open");
  });

  it("资产协议只允许读取 Runtime 账号资产目录", () => {
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
    expect(assetProtocol?.scope).toEqual([
      "$APPLOCALDATA/runtime/accounts/**/*"
    ]);
    expect(assetProtocol?.scope).not.toEqual(
      expect.arrayContaining([
        "$HOME/**",
        "$PICTURE/**",
        "$VIDEO/**",
        "$DOCUMENT/**"
      ])
    );
  });

  it("测试通道使用独立应用标识，避免干扰正式实例", () => {
    const defaultConfig = JSON.parse(
      readFileSync(resolve(process.cwd(), "src-tauri", "tauri.conf.json"), "utf8")
    ) as { identifier?: string };
    const testConfig = JSON.parse(
      readFileSync(resolve(process.cwd(), "src-tauri", "tauri.test.conf.json"), "utf8")
    ) as { identifier?: string };

    expect(testConfig.identifier).toBe("com.tkops.desktop.test");
    expect(testConfig.identifier).not.toBe(defaultConfig.identifier);
  });
});
