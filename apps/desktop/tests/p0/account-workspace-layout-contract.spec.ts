import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

describe("P0 PC 账号工作区布局边界", () => {
  it("全局壳样式受统一入口加载且工作区不使用视口宽度制造溢出", () => {
    const styleIndex = readFileSync(
      join(process.cwd(), "src/styles/index.css"),
      "utf8"
    );
    const css = readFileSync(
      join(
        process.cwd(),
        "src/layouts/account-workspace/account-workspace.css"
      ),
      "utf8"
    );

    expect(styleIndex).toContain('@import "./shell.css";');
    expect(css).toMatch(
      /\.account-workspace-shell\s*\{[\s\S]*?width:\s*100%;[\s\S]*?height:\s*100%;/
    );
    expect(css).not.toMatch(/\.account-workspace-shell\s*\{[\s\S]*?100vw;/);
  });

  it("960px 以下停用工作区壳并展示 PC 窗口提示", () => {
    const css = readFileSync(
      join(
        process.cwd(),
        "src/layouts/account-workspace/account-workspace.css"
      ),
      "utf8"
    );
    const layout = readFileSync(
      join(
        process.cwd(),
        "src/layouts/account-workspace/AccountWorkspaceLayout.vue"
      ),
      "utf8"
    );

    expect(css).toContain("@media (max-width: 959px)");
    expect(css).toMatch(
      /@media \(max-width: 959px\)[\s\S]*?\.account-workspace-shell\s*\{\s*display:\s*none;/
    );
    expect(css).toMatch(
      /@media \(max-width: 959px\)[\s\S]*?\.account-workspace-too-narrow\s*\{\s*display:\s*grid;/
    );
    expect(layout).toContain("当前窗口至少需要 960px 宽度");
    expect(layout).not.toContain("mobile-navigation");
  });

  it("紧凑 PC 窗口只收窄侧栏，不切换成手机导航", () => {
    const css = readFileSync(
      join(
        process.cwd(),
        "src/layouts/account-workspace/account-workspace.css"
      ),
      "utf8"
    );

    expect(css).toContain("@media (max-width: 1279px)");
    expect(css).toMatch(
      /@media \(max-width: 1279px\)[\s\S]*?grid-template-columns:\s*76px minmax\(0, 1fr\);/
    );
    expect(css).not.toContain("position: fixed;\n  bottom: 0;\n  width: 100%");
  });

  it("账号菜单挂载到统一覆盖层并保持四边安全间距", () => {
    const component = readFileSync(
      join(
        process.cwd(),
        "src/layouts/account-workspace/AccountSwitcher.vue"
      ),
      "utf8"
    );
    const css = readFileSync(
      join(
        process.cwd(),
        "src/layouts/account-workspace/account-switcher.css"
      ),
      "utf8"
    );

    expect(component).toContain('<Teleport to="body">');
    expect(component).toContain("Math.min(320");
    expect(component).toContain("Math.max(12");
    expect(css).toMatch(
      /\.account-switcher__menu\s*\{[\s\S]*?position:\s*fixed;/
    );
  });

  it("账号 Detail Panel 在紧凑窗口使用覆盖式抽屉", () => {
    const css = readFileSync(
      join(
        process.cwd(),
        "src/layouts/account-workspace/account-workspace-overlays.css"
      ),
      "utf8"
    );

    expect(css).toContain(".account-detail-overlay");
    expect(css).toContain("position: fixed;");
    expect(css).toContain("width: min(390px, calc(100vw - 76px));");
    expect(css).toContain("@media (prefers-reduced-motion: reduce)");
  });
});
