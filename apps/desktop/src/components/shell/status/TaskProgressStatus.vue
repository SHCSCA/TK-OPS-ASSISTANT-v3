<template>
  <div class="task-progress-status">
    <div class="progress-bar">
      <div class="progress-fill"></div>
    </div>
    <span class="progress-label">正在处理后台任务...</span>
  </div>
</template>

<style scoped>
.task-progress-status {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 240px;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: var(--surface-sunken);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  width: 40%; /* Placeholder */
  background: linear-gradient(90deg, var(--brand-primary), var(--brand-secondary));
  background-size: 200% 100%;
  animation: progress-slide 2s linear infinite;
  border-radius: 2px;
}

.progress-label {
  font-size: 10px;
  color: var(--text-secondary);
  white-space: nowrap;
}

@keyframes progress-slide {
  0% { background-position: 100% 0; }
  100% { background-position: -100% 0; }
}
</style>
