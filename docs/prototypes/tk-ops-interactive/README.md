# TK-OPS 本地交互原型

这是独立于生产应用的 PC 端设计验证稿。它覆盖正式 16 页导航，并重点验证低文字、低噪音、对象优先的 AI 剪辑工作台。

## 启动

在仓库根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File docs/prototypes/tk-ops-interactive/start.ps1
```

然后打开：`http://127.0.0.1:4173/docs/prototypes/tk-ops-interactive/`

也可以直接双击 `index.html`；本地服务器会从仓库根目录提供页面，使原型复用项目内置字体且保持零外部依赖。

## 可交互内容

- 16 页 Sidebar 导航及折叠 / 展开。
- Light / Dark 主题切换。
- 素材与时间线片段选择，选择后展开 Detail Panel。
- 预览播放 / 暂停，空格键可快速切换。
- AI 任务的排队、运行、完成和取消。
- 模拟预览错误、展开技术详情并执行恢复。
- 设置分区、首启流程、队列页面和中性空状态。
- 快捷键：`B` 切换 Sidebar，`D` 切换 Detail Panel，`T` 切换主题，`Esc` 收起浮层。

## 设计边界

- 只适用于 `1600 × 1000`、`1100 × 760` 和最低 `960 × 640` 的 PC 窗口。
- 不接入 Runtime，不创建真实账号、设备、工作区或发布结果。
- 页面中的对象仅用于结构与交互验证，不代表真实业务数据。
- 原型统一通过 `scripts/config.js` 管理运行配置，并通过 `scripts/logger.js` 输出统一日志与可见错误反馈。

## Superdesign 参考

- 静默创作台 Draft：`2aac59f7-2e31-4688-8f1d-9a0650998c7e`
- 本地导出参考：`.superdesign/exports/tk-ops-silent-workbench.html`

浏览器验收结果见 [`VALIDATION.md`](VALIDATION.md)。
