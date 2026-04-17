# B-M15 · 复盘与优化中心 后端

**当前状态（2026-04-17）**: 已完成（V1 摘要、建议生成、状态更新与应用到脚本闭环）。  
**当前接口真源**: `docs/RUNTIME-API-CALLS.md`  
**历史说明**: 以下蓝图创建于 2026-04-14，若与当前代码冲突，以接口真源和当前实现为准。

**前端对应**: M15 `review_optimization_center`  
**优先级**: P3  
**路由前缀**: `/api/review`

---

## 一、数据模型

#### `project_review_summaries`
```python
id: str (PK)
project_id: str (FK → projects.id)
render_count: int
published_count: int
failed_count: int
issue_summary: str | None   # 文字摘要
metrics_json: str | None    # 预留指标扩展
ai_job_id: str | None
created_at: str
```

#### `optimization_suggestions`
```python
id: str (PK)
project_id: str (FK → projects.id)
source_type: str | None   # script / storyboard / render / publish
source_id: str | None     # 具体对象 ID
priority: str             # high / medium / low
category: str             # script / timing / account / technical
title: str
description: str
action_label: str         # "应用到下一版本"
status: str               # pending / applied / dismissed
ai_job_id: str | None
created_at: str
```

---

## 二、API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/review/projects/{project_id}/summary` | 获取项目复盘摘要（统计聚合） |
| POST | `/api/review/projects/{project_id}/summaries/generate` | 触发 AI 摘要生成 |
| GET | `/api/review/projects/{project_id}/suggestions` | 获取优化建议列表 |
| POST | `/api/review/projects/{project_id}/suggestions/generate` | 触发 AI 建议生成 |
| PATCH | `/api/review/suggestions/{id}` | 更新建议状态（applied/dismissed） |
| POST | `/api/review/suggestions/{id}/apply-to-script` | 将建议回流到脚本新版本 |

---

## 三、V1 简化（规则生成建议）

```python
# 不调用 AI，基于规则生成初始建议
def generate_rule_based_suggestions(project_id: str) -> list:
    suggestions = []
    # 规则1: 无成功渲染任务 → 建议完成渲染
    if render_tasks.failed > 0:
        suggestions.append({category: "technical", title: "渲染任务存在失败", priority: "high"})
    # 规则2: 有脚本 → 建议检查分镜版本同步
    if script.revision > storyboard.based_on_script_revision:
        suggestions.append({category: "storyboard", title: "分镜版本落后脚本", priority: "medium"})
    return suggestions
```

---

## 四、新文件清单

```
domain/models/review.py
schemas/review.py
repositories/review_repository.py
services/review_service.py
api/routes/review.py
```

---

## 五、验收标准

- [ ] `GET .../summary` 聚合返回 render_count/published_count/failed_count
- [ ] `GET .../suggestions` 返回建议列表（规则生成，≥2条）
- [ ] 建议状态更新（applied/dismissed）持久化
- [ ] apply-to-script 创建新脚本草稿版本
