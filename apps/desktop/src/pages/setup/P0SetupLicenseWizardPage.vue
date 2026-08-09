<template>
  <main class="p0-setup-page">
    <section class="p0-setup-card">
      <header class="p0-setup-header">
        <span class="p0-setup-logo">TK</span>
        <div>
          <h1>准备 TK-OPS</h1>
          <p>完成本机授权与运行环境检查。</p>
        </div>
        <span class="p0-setup-step">{{ stepLabel }}</span>
      </header>

      <div
        v-if="store.phase === 'loading' && !store.snapshot"
        class="p0-setup-loading"
        role="status"
      >
        <span class="material-symbols-outlined p0-setup-spin">progress_activity</span>
        正在连接本机 Runtime
      </div>

      <section
        v-else-if="store.phase === 'error' && !store.snapshot"
        class="p0-setup-error"
        role="alert"
      >
        <span class="material-symbols-outlined">error</span>
        <div>
          <strong>{{ store.error?.message }}</strong>
          <small v-if="errorReference">{{ errorReference }}</small>
        </div>
        <Button variant="primary" size="sm" @click="store.load">
          重新连接
        </Button>
      </section>

      <template v-else>
        <nav class="p0-setup-progress" aria-label="首启进度">
          <span
            v-for="item in progressItems"
            :key="item.id"
            :data-state="item.state"
          >
            <i>{{ item.index }}</i>
            {{ item.label }}
          </span>
        </nav>

        <div
          v-if="store.snapshot?.license.machineIdentityStatus === 'degraded'"
          class="p0-setup-error"
          role="status"
        >
          <span class="material-symbols-outlined">info</span>
          <div>
            <strong>设备信息采集不完整，稍后自动复检</strong>
            <small>当前许可证仍绑定原机器码，不影响继续使用。</small>
          </div>
          <Button variant="ghost" size="sm" @click="store.refresh">立即复检</Button>
        </div>

        <section v-if="!store.licenseActive" class="p0-setup-panel">
          <div class="p0-setup-panel__heading">
            <div>
              <span>01</span>
              <h2>激活许可证</h2>
            </div>
            <small>本机自动识别</small>
          </div>
          <p>机器码由当前 PC 的稳定硬件信息自动生成，复制后交给授权人员签发许可证。</p>
          <div class="p0-setup-machine-code">
            <div>
              <span>本机机器码</span>
              <code>{{ store.snapshot?.license.machineCode }}</code>
              <small>许可证将绑定这台设备，无需手动填写机器码。</small>
            </div>
            <Button
              variant="secondary"
              size="sm"
              :disabled="!store.snapshot?.license.machineCode"
              @click="copyMachineCode"
            >
              复制机器码
            </Button>
          </div>
          <small
            v-if="machineCodeFeedback"
            class="p0-setup-copy-feedback"
            :data-state="machineCodeCopyFailed ? 'error' : 'success'"
            :role="machineCodeCopyFailed ? 'alert' : 'status'"
          >
            {{ machineCodeFeedback }}
          </small>
          <div class="p0-setup-form">
            <Input
              v-model="licenseKey"
              label="许可证密钥"
              placeholder="粘贴许可证密钥"
              :error="Boolean(fieldError)"
              :hint="fieldError || '密钥仅用于本机激活，不会写入页面配置。'"
            />
          </div>
          <div class="p0-setup-actions">
            <Button
              variant="primary"
              :disabled="store.isBusy"
              :running="store.operation === 'activating_license'"
              @click="handleActivate"
            >
              激活并继续
            </Button>
            <Button
              variant="ghost"
              :disabled="store.isBusy"
              @click="store.refresh"
            >
              刷新状态
            </Button>
          </div>
        </section>

        <section
          v-else-if="store.snapshot?.directories.status !== 'ready'"
          class="p0-setup-panel"
        >
          <div class="p0-setup-panel__heading">
            <div>
              <span>02</span>
              <h2>初始化本地目录</h2>
            </div>
            <small>{{ store.snapshot?.directories.workspaceRootDisplay }}</small>
          </div>
          <p>使用应用数据目录创建账号工作区、资产、渲染与日志边界。</p>
          <ul class="p0-setup-checklist">
            <li
              v-for="item in store.snapshot?.directories.directories"
              :key="item.key"
            >
              <span
                class="material-symbols-outlined"
                :data-state="item.status"
              >
                {{ item.status === "failed" ? "error" : "check_circle" }}
              </span>
              {{ directoryLabel(item.key) }}
            </li>
          </ul>
          <div class="p0-setup-actions">
            <Button
              variant="primary"
              :disabled="store.isBusy"
              :running="store.operation === 'initializing_directories'"
              @click="store.initializeDirectories()"
            >
              初始化目录
            </Button>
          </div>
        </section>

        <section v-else-if="!store.canContinue" class="p0-setup-panel">
          <div class="p0-setup-panel__heading">
            <div>
              <span>03</span>
              <h2>运行环境自检</h2>
            </div>
            <small>{{ runtimeStatusLabel }}</small>
          </div>
          <p>检查数据库、目录、媒体工具与 Runtime 状态。</p>
          <div v-if="store.activeTask" class="p0-setup-task">
            <div>
              <strong>{{ taskStatusLabel }}</strong>
              <span>{{ Math.round(store.activeTask.progress * 100) }}%</span>
            </div>
            <progress :value="store.activeTask.progress" max="1" />
          </div>
          <ul
            v-if="store.snapshot?.blockingIssues.length"
            class="p0-setup-blockers"
          >
            <li
              v-for="issue in store.snapshot.blockingIssues"
              :key="`${issue.code}:${issue.logId}`"
            >
              <strong>{{ issue.message }}</strong>
              <small>{{ issue.code }}<template v-if="issue.logId"> · {{ issue.logId }}</template></small>
            </li>
          </ul>
          <div class="p0-setup-actions">
            <Button
              variant="primary"
              :disabled="store.isBusy"
              :running="store.operation === 'running_self_checks'"
              @click="store.runSelfChecks"
            >
              开始自检
            </Button>
            <Button
              v-if="store.operation === 'running_self_checks'"
              variant="ghost"
              @click="store.cancelSelfChecks"
            >
              取消
            </Button>
            <Button
              v-else
              variant="ghost"
              :disabled="store.isBusy"
              @click="store.refresh"
            >
              重新读取
            </Button>
          </div>
        </section>

        <section v-else class="p0-setup-complete">
          <span class="material-symbols-outlined">check_circle</span>
          <h2>本机环境已就绪</h2>
          <p>现在可以进入账号工作区。尚未添加账号时会显示真实空状态。</p>
          <Button variant="primary" size="lg" @click="continueToWorkspace">
            进入工作区
          </Button>
        </section>

        <aside
          v-if="store.error && store.snapshot"
          class="p0-setup-inline-error"
          role="alert"
        >
          <span class="material-symbols-outlined">warning</span>
          <span>
            {{ store.error.message }}
            <small v-if="errorReference">{{ errorReference }}</small>
          </span>
        </aside>
      </template>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { resolveInternalRedirect } from "@/app/router/internal-redirect";
import Button from "@/components/ui/Button/Button.vue";
import Input from "@/components/ui/Input/Input.vue";
import { useP0BootstrapStore } from "@/modules/system/bootstrap-store";

import "./p0-setup.css";

const store = useP0BootstrapStore();
const route = useRoute();
const router = useRouter();
const licenseKey = ref("");
const fieldError = ref("");
const machineCodeFeedback = ref("");
const machineCodeCopyFailed = ref(false);

const progressItems = computed(() => [
  {
    id: "license",
    index: 1,
    label: "许可证",
    state: store.licenseActive ? "done" : "current"
  },
  {
    id: "directories",
    index: 2,
    label: "本地目录",
    state:
      store.snapshot?.directories.status === "ready"
        ? "done"
        : store.licenseActive
          ? "current"
          : "pending"
  },
  {
    id: "runtime",
    index: 3,
    label: "环境自检",
    state: store.canContinue
      ? "done"
      : store.snapshot?.directories.status === "ready"
        ? "current"
        : "pending"
  }
]);

const stepLabel = computed(() => {
  if (store.canContinue) return "已就绪";
  if (!store.licenseActive) return "步骤 1 / 3";
  if (store.snapshot?.directories.status !== "ready") return "步骤 2 / 3";
  return "步骤 3 / 3";
});

const runtimeStatusLabel = computed(() => {
  const runtime = store.snapshot?.runtime.status;
  const media = store.snapshot?.mediaTools.status;
  if (runtime === "ready" && media === "ready") return "基础服务可用";
  if (runtime === "failed" || media === "failed") return "需要修复";
  return "等待检查";
});

const taskStatusLabel = computed(() => {
  switch (store.activeTask?.status) {
    case "queued":
      return "自检已排队";
    case "running":
      return "正在自检";
    case "cancelling":
      return "正在取消";
    case "completed":
      return store.activeTask.completionKind === "cancelled"
        ? "自检已取消"
        : "自检完成";
    case "failed":
      return "自检失败";
    default:
      return "等待自检";
  }
});

const errorReference = computed(() => {
  if (store.error?.logId) return `日志：${store.error.logId}`;
  if (store.error?.requestId) return `请求：${store.error.requestId}`;
  return "";
});

onMounted(() => {
  if (store.phase === "idle") {
    void store.load();
  }
});

async function handleActivate(): Promise<void> {
  fieldError.value = "";
  if (!licenseKey.value.trim()) {
    fieldError.value = "许可证密钥不能为空。";
    return;
  }
  const activated = await store.activateLicense(licenseKey.value);
  if (activated) {
    licenseKey.value = "";
  }
}

async function copyMachineCode(): Promise<void> {
  const machineCode = store.snapshot?.license.machineCode;
  machineCodeFeedback.value = "";
  machineCodeCopyFailed.value = false;
  if (!machineCode) {
    machineCodeCopyFailed.value = true;
    machineCodeFeedback.value = "机器码尚未生成，请刷新状态后重试。";
    return;
  }
  try {
    if (!navigator.clipboard) {
      throw new Error("当前环境不支持剪贴板写入");
    }
    await navigator.clipboard.writeText(machineCode);
    machineCodeFeedback.value = "机器码已复制。";
  } catch {
    machineCodeCopyFailed.value = true;
    machineCodeFeedback.value = "复制失败，请选中机器码后手动复制。";
  }
}

async function continueToWorkspace(): Promise<void> {
  await router.replace(
    resolveInternalRedirect(route.query.redirect, "/workspace")
  );
}

function directoryLabel(key: string): string {
  const labels: Record<string, string> = {
    data_root: "应用数据",
    projects: "账号工作区",
    assets: "内容资产",
    renders: "渲染输出",
    cache: "运行缓存",
    exports: "导出文件",
    logs: "诊断日志",
    licenses: "许可证"
  };
  return labels[key] ?? key;
}
</script>
