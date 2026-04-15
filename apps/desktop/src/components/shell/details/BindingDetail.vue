<template>
  <div class="binding-detail">
    <section class="detail-section">
      <p class="detail-section__title">账号绑定状态</p>
      <div class="account-card">
        <span class="material-symbols-outlined">account_circle</span>
        <div class="account-info">
          <p class="account-name">未绑定账号</p>
          <p class="account-hint">绑定 TikTok 账号以开启自动化发布</p>
        </div>
      </div>
    </section>
    
    <section class="detail-section">
      <p class="detail-section__title">安全建议</p>
      <div class="security-well">
        <span class="material-symbols-outlined">verified_user</span>
        <p>您的所有授权凭证均加密存储在本地，不会上传至云端。</p>
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

.account-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--surface-tertiary);
  padding: 12px;
  border-radius: var(--radius-md);
}

.account-card .material-symbols-outlined {
  font-size: 32px;
  color: var(--text-tertiary);
}

.account-name {
  font-size: 14px;
  font-weight: 700;
  margin: 0;
}

.account-hint {
  font-size: 11px;
  color: var(--text-tertiary);
  margin: 2px 0 0;
}

.security-well {
  background: color-mix(in srgb, var(--status-success) 5%, transparent);
  padding: 12px;
  border-radius: var(--radius-md);
  display: flex;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.4;
}

.security-well .material-symbols-outlined {
  color: var(--status-success);
  font-size: 18px;
  flex-shrink: 0;
}
</style>
