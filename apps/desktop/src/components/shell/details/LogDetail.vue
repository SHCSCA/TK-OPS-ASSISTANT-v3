<template>
  <div class="log-detail">
    <section class="detail-section">
      <div class="detail-section__header">
        <p class="detail-section__title">实时任务日志</p>
        <button class="text-btn">清空</button>
      </div>
      <div class="log-viewport">
        <div class="log-line system">[SYSTEM] 初始化日志引擎...</div>
        <div class="log-line info">[INFO] 等待任务投递...</div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.log-detail {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.detail-section {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.detail-section__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.detail-section__title {
  color: var(--text-tertiary);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.05em;
  margin: 0;
  text-transform: uppercase;
}

.text-btn {
  background: transparent;
  border: none;
  color: var(--brand-primary);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.log-viewport {
  flex: 1;
  background: #000;
  border-radius: var(--radius-md);
  padding: 12px;
  font-family: var(--font-mono);
  font-size: 11px;
  overflow-y: auto;
}

.log-line {
  margin-bottom: 4px;
  line-height: 1.4;
}

.log-line.system { color: var(--brand-primary); }
.log-line.info { color: #888; }
</style>
