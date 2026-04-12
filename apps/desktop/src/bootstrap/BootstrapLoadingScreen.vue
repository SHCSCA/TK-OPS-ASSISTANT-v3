<template>
  <section class="bootstrap-screen" data-bootstrap-screen="loading">
    <div class="bootstrap-screen__backdrop" aria-hidden="true" />
    <div class="bootstrap-screen__panel">
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
