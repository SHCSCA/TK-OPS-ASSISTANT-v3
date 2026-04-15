<template>
  <div class="asset-detail">
    <section class="detail-section">
      <p class="detail-section__title">资产预览</p>
      <div class="asset-preview-well">
        <span class="material-symbols-outlined">image</span>
        <p>未选中资产</p>
      </div>
    </section>
    
    <section class="detail-section">
      <p class="detail-section__title">属性与元数据</p>
      <div class="metadata-list">
        <p class="empty-hint">在左侧列表中选择一个资产以查看其详细属性。</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.detail-section {
  border-bottom: 1px solid var(--border-default);
  padding: 16px 0;
}

.detail-section__title {
  color: var(--text-tertiary);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.05em;
  margin: 0 0 12px;
  text-transform: uppercase;
}

.asset-preview-well {
  aspect-ratio: 16/9;
  background: var(--surface-sunken);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
}

.asset-preview-well .material-symbols-outlined {
  font-size: 48px;
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 13px;
  color: var(--text-tertiary);
  font-style: italic;
  text-align: center;
  padding: 24px 0;
}
</style>
