export const accountWorkspaces = {
  mirror: {
    account: {
      id: "mirror",
      initials: "镜",
      name: "镜头 A",
      platform: "TikTok",
      positioning: "AI 工具讲解",
      status: "online",
    },
    strategy: {
      summary: "把复杂 AI 工具讲成 60 秒内可执行的工作流。",
      version: "定位 v4",
      pillars: ["工具拆解", "效率实验", "真实复盘"],
      rules: ["开头先给结果", "每条只讲一个动作", "避免收益承诺"],
    },
    knowledge: [
      { id: "m-k1", type: "品牌资料", name: "账号表达与禁用词", status: "ready", updated: "今天" },
      { id: "m-k2", type: "参考内容", name: "高留存口播样本", status: "ready", updated: "昨天" },
      { id: "m-k3", type: "产品文档", name: "AI 工具功能清单", status: "stale", updated: "7 天前" },
      { id: "m-k4", type: "视频拆解", name: "对标账号镜头节奏", status: "error", updated: "刚刚" },
    ],
    topics: [
      { id: "m-t1", title: "三步整理混乱提示词", pillar: "工具拆解", selected: true },
      { id: "m-t2", title: "一周自动化复盘", pillar: "真实复盘", selected: true },
      { id: "m-t3", title: "桌面端批量生成流程", pillar: "效率实验", selected: false },
      { id: "m-t4", title: "知识库为什么会串号", pillar: "工具拆解", selected: false },
    ],
    batches: [
      { id: "m-b1", name: "本周 AI 工具拆解", stage: "生成", progress: 68, status: "running", updated: "10 分钟前", items: 8 },
      { id: "m-b2", name: "效率实验系列", stage: "脚本", progress: 34, status: "running", updated: "1 小时前", items: 6 },
      { id: "m-b3", name: "复盘内容补充", stage: "待发布", progress: 100, status: "ready", updated: "昨天", items: 4 },
    ],
    exceptions: [
      { id: "m-e1", title: "镜头素材缺失", detail: "内容 03 · 产品操作画面未找到", tone: "danger", action: "补充素材" },
      { id: "m-e2", title: "字幕可能溢出", detail: "内容 06 · 第 4 句超过安全宽度", tone: "warning", action: "重新对齐" },
    ],
    variants: [
      { id: "m-v1", title: "三步整理混乱提示词", status: "completed", version: "v3", duration: "00:42", issue: null },
      { id: "m-v2", title: "一周自动化复盘", status: "review", version: "v2", duration: "00:51", issue: "镜头 04 低置信" },
      { id: "m-v3", title: "桌面端批量生成流程", status: "running", version: "v1", duration: "--:--", issue: null },
      { id: "m-v4", title: "知识库为什么会串号", status: "failed", version: "v1", duration: "--:--", issue: "缺少参考素材" },
    ],
    library: [
      { id: "m-l1", title: "三步整理混乱提示词", kind: "成片", source: "本周 AI 工具拆解", version: "v3", status: "ready", aiSource: { node: "合成 / BGM", model: "FFmpeg Template", recipe: "清晰口播 v2" } },
      { id: "m-l2", title: "AI 工具讲解口播模板", kind: "模板", source: "账号知识库", version: "v4", status: "ready" },
      { id: "m-l3", title: "桌面端录屏素材", kind: "素材", source: "本地工作区", version: "12 项", status: "missing" },
    ],
    publishing: [
      { id: "m-p1", title: "三步整理混乱提示词", schedule: "今天 20:30", status: "preflight", binding: "主工作区" },
      { id: "m-p2", title: "一周自动化复盘", schedule: "明天 12:00", status: "blocked", binding: "主工作区" },
    ],
    review: [
      { id: "m-r1", title: "缩短开场解释", evidence: "已连接内容的前段停留反馈", target: "定位" },
      { id: "m-r2", title: "补充真实操作镜头样本", evidence: "两条内容的镜头置信度偏低", target: "知识" },
      { id: "m-r3", title: "下周增加效率实验占比", evidence: "演示建议，仅验证回流交互", target: "计划" },
    ],
  },
  focus: {
    account: {
      id: "focus",
      initials: "F",
      name: "Focus Lab",
      platform: "TikTok",
      positioning: "Desktop productivity",
      status: "online",
    },
    strategy: {
      summary: "Quiet desktop workflows for makers who want fewer tools and cleaner routines.",
      version: "Positioning v2",
      pillars: ["Deep work", "Desk systems", "Weekly reset"],
      rules: ["Show the workflow first", "Use calm pacing", "No productivity guilt"],
    },
    knowledge: [
      { id: "f-k1", type: "Brand notes", name: "Tone and visual language", status: "ready", updated: "Today" },
      { id: "f-k2", type: "References", name: "Quiet desk workflow clips", status: "ready", updated: "2 days ago" },
      { id: "f-k3", type: "Research", name: "Focus routine interview notes", status: "stale", updated: "9 days ago" },
    ],
    topics: [
      { id: "f-t1", title: "A 10-minute weekly desktop reset", pillar: "Weekly reset", selected: true },
      { id: "f-t2", title: "One-screen deep work setup", pillar: "Deep work", selected: false },
      { id: "f-t3", title: "Calmer file naming in three rules", pillar: "Desk systems", selected: true },
    ],
    batches: [
      { id: "f-b1", name: "Quiet desktop routines", stage: "合成", progress: 84, status: "running", updated: "18 min ago", items: 5 },
      { id: "f-b2", name: "Weekly reset scripts", stage: "分镜", progress: 46, status: "running", updated: "3 hours ago", items: 4 },
    ],
    exceptions: [
      { id: "f-e1", title: "Voice profile unavailable", detail: "Variant 02 · fallback voice needs confirmation", tone: "warning", action: "Choose voice" },
    ],
    variants: [
      { id: "f-v1", title: "A 10-minute weekly desktop reset", status: "completed", version: "v2", duration: "00:38", issue: null },
      { id: "f-v2", title: "One-screen deep work setup", status: "review", version: "v1", duration: "00:44", issue: "Confirm fallback voice" },
      { id: "f-v3", title: "Calmer file naming in three rules", status: "running", version: "v1", duration: "--:--", issue: null },
    ],
    library: [
      { id: "f-l1", title: "Weekly desktop reset", kind: "Video", source: "Quiet desktop routines", version: "v2", status: "ready", aiSource: { node: "图片 / 视频", model: "Kling I2V", recipe: "安静桌面 v1" } },
      { id: "f-l2", title: "Soft-spoken workflow template", kind: "Template", source: "Account knowledge", version: "v2", status: "ready" },
    ],
    publishing: [
      { id: "f-p1", title: "A 10-minute weekly desktop reset", schedule: "Tomorrow 09:00", status: "ready", binding: "Focus workspace" },
    ],
    review: [
      { id: "f-r1", title: "Keep the opening under five seconds", evidence: "Connected-content intro feedback", target: "Positioning" },
      { id: "f-r2", title: "Add two close-up desk references", evidence: "Visual confidence check", target: "Knowledge" },
    ],
  },
};

export function cloneAccountWorkspaces() {
  return structuredClone(accountWorkspaces);
}
