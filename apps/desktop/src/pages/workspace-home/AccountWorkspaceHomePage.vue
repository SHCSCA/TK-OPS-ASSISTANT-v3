<template>
  <main
    class="workspace-home"
    data-testid="account-workspace-home"
  >
    <section
      v-if="!accountId"
      class="workspace-home-state"
      data-state="dependency_blocked"
    >
      <span class="material-symbols-outlined" aria-hidden="true">
        account_circle
      </span>
      <h1>请选择账号工作区</h1>
      <p>选择账号后，这里只显示该账号的就绪状态与任务。</p>
    </section>

    <section
      v-else-if="!activeContext"
      class="workspace-home-state"
      data-state="loading"
      aria-busy="true"
      aria-live="polite"
    >
      <span class="workspace-home-spinner" aria-hidden="true" />
      <h1>正在载入账号工作区</h1>
      <p>切换完成前不会展示其他账号的数据。</p>
    </section>

    <template v-else>
      <section class="workspace-home-hero">
        <div class="workspace-home-identity">
          <span class="workspace-home-avatar" aria-hidden="true">
            {{ accountInitial(activeContext.account) }}
          </span>
          <div class="workspace-home-identity__copy">
            <p class="workspace-home-eyebrow">当前 TikTok 账号</p>
            <div class="workspace-home-title-row">
              <h1>{{ activeContext.account.name }}</h1>
              <span
                class="workspace-home-account-status"
                :data-tone="accountStatusTone(activeContext.account.status)"
              >
                {{ accountStatusLabel(activeContext.account.status) }}
              </span>
            </div>
            <p class="workspace-home-handle">
              {{ accountIdentityLabel(activeContext.account) }}
            </p>
            <p class="workspace-home-positioning">
              {{
                activeContext.account.positioningSummary
                  || "尚未设置账号定位摘要"
              }}
            </p>
          </div>
        </div>

        <div class="workspace-home-next">
          <p>{{ nextAction.description }}</p>
          <p
            v-if="nextAction.feedback"
            class="workspace-home-action-feedback"
            role="alert"
            data-testid="workspace-action-feedback"
          >
            {{ nextAction.feedback }}
          </p>
          <RouterLink
            class="workspace-home-primary-action"
            :to="nextAction.to"
            data-testid="workspace-next-action"
          >
            {{ nextAction.label }}
            <span class="material-symbols-outlined" aria-hidden="true">
              arrow_forward
            </span>
          </RouterLink>
        </div>
      </section>

      <div class="workspace-home-grid">
        <section
          class="workspace-home-panel workspace-home-panel--readiness"
          aria-labelledby="workspace-readiness-title"
        >
          <header class="workspace-home-section-header">
            <div>
              <p class="workspace-home-eyebrow">开始生产前</p>
              <h2 id="workspace-readiness-title">账号就绪度</h2>
            </div>
            <span
              class="workspace-home-overall"
              :data-status="activeContext.readiness.overall"
            >
              {{ workspaceOverallLabel(activeContext.readiness.overall) }}
            </span>
          </header>

          <div class="workspace-home-readiness-list">
            <article
              v-for="readiness in readinessViews"
              :key="readiness.key"
              class="workspace-home-readiness-item"
              :data-status="readiness.item.status"
            >
              <span
                class="material-symbols-outlined workspace-home-readiness-icon"
                aria-hidden="true"
              >
                {{ readiness.icon }}
              </span>
              <div>
                <span>{{ readiness.label }}</span>
                <strong>{{ readinessShortLabel(readiness.item) }}</strong>
                <p>{{ readiness.item.label }}</p>
              </div>
            </article>
          </div>
        </section>

        <section
          class="workspace-home-panel workspace-home-panel--tasks"
          aria-labelledby="workspace-task-title"
        >
          <header class="workspace-home-section-header">
            <div>
              <p class="workspace-home-eyebrow">当前账号范围</p>
              <h2 id="workspace-task-title">任务概况</h2>
            </div>
            <span class="material-symbols-outlined" aria-hidden="true">
              task_alt
            </span>
          </header>

          <dl class="workspace-home-task-summary">
            <div data-tone="running">
              <dt>运行中</dt>
              <dd data-testid="workspace-running-count">
                {{ activeContext.taskSummary.running }}
              </dd>
            </div>
            <div data-tone="failed">
              <dt>失败</dt>
              <dd data-testid="workspace-failed-count">
                {{ activeContext.taskSummary.failed }}
              </dd>
            </div>
          </dl>

          <p
            v-if="
              activeContext.taskSummary.running === 0
              && activeContext.taskSummary.failed === 0
            "
            class="workspace-home-task-note"
          >
            当前没有运行中或失败任务。
          </p>
          <p v-else class="workspace-home-task-note">
            状态来自当前账号的 Runtime 任务汇总。
          </p>
        </section>
      </div>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed } from "vue";

import {
  accountIdentityLabel,
  accountInitial,
  accountStatusLabel,
  accountStatusTone,
  readinessShortLabel
} from "@/modules/accounts/account-formatters";
import type { AccountWorkspaceContextDto } from "@/types/runtime/accounts";

import {
  createWorkspaceNextAction,
  createWorkspaceReadinessViews,
  workspaceOverallLabel
} from "./workspace-home-view";
import "./workspace-home.css";

const props = withDefaults(defineProps<{
  accountId?: string | null;
  workspaceContext?: AccountWorkspaceContextDto | null;
}>(), {
  accountId: null,
  workspaceContext: null
});

const activeContext = computed(() => {
  if (
    !props.accountId
    || props.workspaceContext?.account.id !== props.accountId
  ) {
    return null;
  }
  return props.workspaceContext;
});

const readinessViews = computed(() =>
  activeContext.value
    ? createWorkspaceReadinessViews(activeContext.value)
    : []
);

const nextAction = computed(() =>
  activeContext.value
    ? createWorkspaceNextAction(activeContext.value)
    : {
        description: "",
        feedback: null,
        label: "",
        to: { name: "account_workspace_home" }
      }
);
</script>
