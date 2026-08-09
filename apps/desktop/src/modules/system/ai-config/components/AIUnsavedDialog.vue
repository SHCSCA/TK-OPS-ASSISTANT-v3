<template>
  <div v-if="open" class="ai-modal-backdrop" @click.self="$emit('cancel')">
    <section class="ai-dialog" role="alertdialog" aria-modal="true">
      <header>
        <span class="material-symbols-outlined">edit_note</span>
        <div>
          <h2>处理未保存配置</h2>
          <p>{{ label }}包含未保存内容。保存失败时会留在当前工作面。</p>
        </div>
      </header>
      <footer>
        <button class="ai-button is-quiet" type="button" @click="$emit('cancel')">
          返回编辑
        </button>
        <button class="ai-button is-danger" type="button" @click="$emit('discard')">
          放弃并继续
        </button>
        <button
          class="ai-button is-primary"
          type="button"
          :disabled="busy"
          @click="$emit('save')"
        >
          {{ busy ? "保存中…" : "保存并继续" }}
        </button>
      </footer>
    </section>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ busy?: boolean; label?: string; open: boolean }>(), {
  busy: false,
  label: "当前编辑器"
});

defineEmits<{ cancel: []; discard: []; save: [] }>();
</script>
