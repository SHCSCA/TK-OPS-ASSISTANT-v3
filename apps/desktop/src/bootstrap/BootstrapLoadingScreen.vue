<template>
  <section class="bootstrap-screen" data-bootstrap-screen="loading">
    <div class="bootstrap-screen__backdrop" aria-hidden="true" />
    <div class="bootstrap-screen__aurora" aria-hidden="true" />
    <div class="bootstrap-screen__panel bootstrap-loading__panel-enter">
      <p class="bootstrap-screen__eyebrow">TK-OPS 启动检查</p>
      <h1>正在准备首启环境</h1>
      <p class="bootstrap-screen__summary">
        系统正在准备本地创作工作台，连接 Runtime、读取配置、校验授权，并准备进入首启初始化流程。
      </p>

      <ol class="bootstrap-screen__steps">
        <li class="bootstrap-screen__step">
          <span class="bootstrap-screen__dot bootstrap-screen__dot--loading" />
          <span>连接本地 Runtime</span>
        </li>
        <li class="bootstrap-screen__step">
          <span class="bootstrap-screen__dot bootstrap-screen__dot--loading" />
          <span>读取系统配置</span>
        </li>
        <li class="bootstrap-screen__step">
          <span class="bootstrap-screen__dot bootstrap-screen__dot--loading" />
          <span>检查许可证状态</span>
        </li>
        <li class="bootstrap-screen__step">
          <span class="bootstrap-screen__dot bootstrap-screen__dot--pending" />
          <span>准备初始化向导</span>
        </li>
      </ol>
    </div>
  </section>
</template>

<style scoped>
/* 极光背景旋转——即使 Runtime 离线也有动效反馈 */
.bootstrap-screen__aurora {
  position: absolute;
  inset: -40%;
  background: var(--gradient-aurora);
  filter: blur(80px);
  opacity: 0.35;
  animation: aurora-rotate var(--motion-rotate-slow) linear infinite;
  pointer-events: none;
  z-index: -1;
}

/* 面板入场：从下方淡入 */
.bootstrap-loading__panel-enter {
  animation: bootstrap-panel-in var(--motion-slow) var(--ease-decelerate) both;
}

@keyframes bootstrap-panel-in {
  from {
    opacity: 0;
    transform: translateY(24px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>
