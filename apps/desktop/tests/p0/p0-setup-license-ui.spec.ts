import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useP0BootstrapStore } from "@/modules/system/bootstrap-store";
import P0SetupLicenseWizardPage from "@/pages/setup/P0SetupLicenseWizardPage.vue";
import type { BootstrapStatusDto } from "@/types/runtime/bootstrap";

const bootstrapApi = vi.hoisted(() => ({
  activateBootstrapLicense: vi.fn(),
  fetchBootstrapStatus: vi.fn(),
  initializeBootstrapDirectories: vi.fn(),
  startBootstrapSelfChecks: vi.fn()
}));

vi.mock("@/app/runtime-client/bootstrap", () => bootstrapApi);

describe("P0 首启许可证 UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("展示 Runtime 自动生成的完整机器码并支持复制", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText }
    });
    const { wrapper } = await mountLicensePage(missingLicenseFixture());

    expect(wrapper.text()).toContain(MACHINE_CODE);
    expect(wrapper.text()).toContain("无需手动填写机器码");
    expect(wrapper.findAll("input")).toHaveLength(1);

    await buttonByText(wrapper, "复制机器码").trigger("click");
    await flushPromises();

    expect(writeText).toHaveBeenCalledWith(MACHINE_CODE);
    expect(wrapper.text()).toContain("机器码已复制");
  });

  it("激活请求只提交许可证密钥，机器码由 Runtime 绑定", async () => {
    const missing = missingLicenseFixture();
    const active = activeLicenseFixture();
    bootstrapApi.activateBootstrapLicense.mockResolvedValue({
      data: active.license,
      meta: null,
      operationId: "op-license",
      requestId: "request-license",
      status: 200
    });
    bootstrapApi.fetchBootstrapStatus.mockResolvedValue({
      data: active,
      meta: null,
      operationId: "op-refresh",
      requestId: "request-refresh",
      status: 200
    });
    const { wrapper } = await mountLicensePage(missing);

    await wrapper.get("input").setValue("  signed.license  ");
    await buttonByText(wrapper, "激活并继续").trigger("click");
    await flushPromises();

    expect(bootstrapApi.activateBootstrapLicense).toHaveBeenCalledWith(
      { licenseKey: "signed.license" },
      expect.objectContaining({
        idempotencyKey: expect.stringContaining("bootstrap-license")
      })
    );
  });
});

const MACHINE_CODE = "TKOPS-ABCDE-FGHIJ-KLMNO-PQRST-UVWXY";

async function mountLicensePage(snapshot: BootstrapStatusDto) {
  const pinia = createPinia();
  setActivePinia(pinia);
  const store = useP0BootstrapStore();
  store.phase = "setup_required";
  store.snapshot = snapshot;
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/setup/license",
        component: { template: "<div />" }
      }
    ]
  });
  await router.push("/setup/license");
  await router.isReady();
  const wrapper = mount(P0SetupLicenseWizardPage, {
    global: { plugins: [pinia, router] }
  });
  return { store, wrapper };
}

function buttonByText(
  wrapper: ReturnType<typeof mount>,
  label: string
) {
  const button = wrapper.findAll("button").find((item) => item.text() === label);
  if (!button) {
    throw new Error(`未找到按钮：${label}`);
  }
  return button;
}

function missingLicenseFixture(): BootstrapStatusDto {
  return {
    license: {
      status: "missing",
      machineCode: MACHINE_CODE,
      machineCodeMasked: "TKOPS-************************UVWXY",
      expiresAt: null,
      activatedAt: null,
      blockingIssue: {
        code: "LICENSE_MISSING",
        message: "许可证尚未激活"
      },
      revision: 0,
      machineIdentityStatus: "verified",
      machineIdentityAlgorithm: "v2",
      matchedFactorCount: 3,
      mismatchedFactorCount: 0,
      unavailableFactorCount: 0
    },
    directories: {
      status: "attention",
      workspaceRootDisplay: "应用数据目录",
      directories: [],
      issues: [],
      revision: 0
    },
    runtime: { status: "ready", version: "0.4.7" },
    mediaTools: { status: "ready", issues: [] },
    canContinue: false,
    blockingIssues: [
      {
        code: "LICENSE_MISSING",
        message: "许可证尚未激活",
        logId: null
      }
    ],
    revision: 0
  };
}

function activeLicenseFixture(): BootstrapStatusDto {
  const snapshot = missingLicenseFixture();
  return {
    ...snapshot,
    license: {
      ...snapshot.license,
      status: "active",
      activatedAt: "2026-08-01T10:00:00Z",
      blockingIssue: null,
      revision: 1
    },
    blockingIssues: [],
    revision: 1
  };
}
