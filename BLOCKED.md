# 待裁决清单

P0-H H1-H4 生产实现与自动化验收已完成；H5 脱敏证据、四制品绑定和 Production 门禁工具已实现，但仍缺目标机器真实 OpenAI-compatible Provider 调用证据。版本继续保持 `0.4.11`，在 H5 人工门禁完成前不得宣称 `0.5.0` 或 Production 完成。

## 已解除：P0-H 规格工作树白名单（历史）

用户已授权谨慎处理既存差异。为避免纯 stash 隔离把源码暂时回退到 Git HEAD 的 0.4.7，既有真实 0.4.11 源码已在独立本地分支形成安全基线；规格批准前的工作区曾只保留四份 P0-H 文档，批准后的 H1-H5 实施已按规格扩展到生产代码、测试与接口文档：

1. 原始完整可见状态：`2a1079de64d62e00fbbed95862a34dd895e43ae0`，保存 1384 个外部文件。
2. `.gitignore` 还原后显现的历史忽略产物：`6b1dcad7b8fa0603c6ce43a16b5663e68475c75c`，保存 668 个文件。
3. 原型 npm 缓存与截图临时文件：`b5ea8a0de0a2d1fc786b8f77e743d18f849b9c2d`；该 stash 避免约 150 MB 缓存进入 Git 历史。
4. 三份 stash 均为本地 commit 对象并保留三个父提交，未执行 pop、drop、覆盖或删除；恢复应使用不可变哈希，不依赖会变化的 `stash@{n}` 序号。
5. 独立本地分支为 `codex/p0h-baseline-snapshot`，安全基线提交为 `bec7844452bce4e6a1559debc1903e30ba4bb03a`；提交包含 990 个既有路径，四文档白名单命中数为 0，没有上游且未推送。

当前分支已包含真实 0.4.11 源码，不得再次应用原始完整快照。只有确需恢复本地产物时，才按用途应用以下快照：

```powershell
git stash apply 6b1dcad7b8fa0603c6ce43a16b5663e68475c75c
git stash apply b5ea8a0de0a2d1fc786b8f77e743d18f849b9c2d
```

如需在 `main` 重建隔离前的完整工作树，应先另行保护当前四文档，再在 `main` 依次应用 `2a1079de64d62e00fbbed95862a34dd895e43ae0` 与 `6b1dcad7b8fa0603c6ce43a16b5663e68475c75c`；本轮不执行该恢复操作。

## P0-H 规格任务历史阻断证据

1. 任务 0 三组基线命令全部符合预期，不存在版本、pending 数量、规格数量或目标目录偏差。
2. 本任务开工前 `git status --porcelain=v1` 已有 337 条记录，且仓库级 `git diff --name-only` 已列出大量四文档白名单外的既存改动。相同粒度的前三轮审计均为 `白名单4 + 外部334`，白名单外增量 0。该历史阻断已在用户授权后通过独立本地基线提交与三份安全 stash 解除，没有丢失或覆盖原改动。
3. 真实 OpenAI-compatible API Key 按任务书约定须在目标机器由用户人工提供；自动化只允许使用受控 Provider 验证协议，不能冒充 H5 真实 Provider 证据。

## P0-H 规格任务裁决

1. 规格内容、四份允许文档、红灯到绿灯、结构、编码和尾随空白门禁均已完成并有实际命令证据。
2. 原始仓库白名单阻断曾连续三轮复现；用户授权后已用独立分支、本地基线提交和可恢复 stash 解除，最终门禁以当前四文档工作区重新执行。
3. 本节为规格阶段历史裁决；当前 H1-H4 已实现并通过自动化门禁，但工作树门禁解除仍不代表 H5 真实 Provider 调用或 `0.5.0` 制品已经完成。

## Production 提升未满足项

1. 尚缺目标机器基于当前 0.4.11 Desktop、Runtime 与安装包哈希生成的真实 TikTok 可见浏览器监督登录证据。
2. 尚缺目标机器真实 OpenAI-compatible Provider 的 `script_generation` 成功调用、reported usage、脱敏 evidence 与当前四制品 SHA-256 绑定；受控 Provider E2E 不满足此门禁。
3. 当前 release manifest 为 `channel=test`、`dirty=true`；Production 提升要求干净提交重新构建，并禁止复用旧源快照证据。
4. 上述事项不阻止当前自动化测试候选继续验证，但在满足前不得覆盖 `dist/releases/current.json` 或宣称 Production 上线完成。
5. P0-I 创作生产链尚未实施，八个正式业务路由继续保持 pending，不得计入“全产品完成”。
