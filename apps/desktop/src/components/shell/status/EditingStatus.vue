<template>
  <div class="editing-status">
    <div class="timecode-box">
      <span class="material-symbols-outlined">timer</span>
      <span class="timecode">00:00:00:00</span>
    </div>
    <div class="save-badge">
      <span class="dot"></span>
      <span>自动保存中...</span>
    </div>
  </div>
</template>

<style scoped>
.editing-status {
  display: flex;
  align-items: center;
  gap: 16px;
}

.timecode-box {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--brand-primary);
  font-family: var(--font-mono);
  font-weight: 700;
}

.timecode-box .material-symbols-outlined {
  font-size: 14px;
}

.timecode {
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.05em;
}

.save-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  color: var(--text-tertiary);
}

.dot {
  width: 4px;
  height: 4px;
  background: var(--status-success);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
</style>
