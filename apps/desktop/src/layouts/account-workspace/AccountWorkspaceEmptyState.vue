<template>
  <main class="account-workspace-empty">
    <div>
      <span
        class="material-symbols-outlined account-workspace-empty__icon"
        aria-hidden="true"
      >
        account_circle
      </span>
      <h2>选择一个账号工作区</h2>
      <p>定位、知识、内容与任务按 TikTok 账号独立保存。</p>
      <div class="account-workspace-empty__actions">
        <button
          class="account-workspace-empty__primary"
          type="button"
          @click="emit('select')"
        >
          选择账号
        </button>
        <button type="button" @click="emit('add')">添加账号</button>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
const emit = defineEmits<{
  add: [];
  select: [];
}>();
</script>
