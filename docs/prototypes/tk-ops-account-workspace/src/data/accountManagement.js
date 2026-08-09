export const accountStatusMeta = {
  archived: { label: "已归档", tone: "muted", action: "查看" },
  attention: { label: "需处理", tone: "danger", action: "修复" },
  draft: { label: "草稿", tone: "muted", action: "继续配置" },
  ready: { label: "可用", tone: "ready", action: "切换" },
  unbound: { label: "未绑定", tone: "warning", action: "完成连接" },
};

export const accountProfiles = [
  {
    id: "mirror",
    initials: "镜",
    name: "镜头 A",
    platform: "TikTok",
    positioning: "把复杂 AI 工具讲成 60 秒内可执行的工作流",
    shortPositioning: "AI 工具讲解",
    status: "ready",
    recent: "10 分钟前",
    readiness: { connection: "ready", knowledge: "ready", ai: "ready" },
    connection: { workspace: "G:/TK-OPS/mirror", browser: "Chrome 演示实例", environment: "本机 Runtime" },
    recipe: { id: "recipe-talk", name: "清晰口播", script: "GPT-5.4 mini", visual: "Flux 快速图", video: "Seedance Lite", voice: "清亮中性", ratio: "9:16", inheritance: "账号覆盖 2 项" },
  },
  {
    id: "focus",
    initials: "F",
    name: "Focus Lab",
    platform: "TikTok",
    positioning: "Quiet desktop workflows for makers",
    shortPositioning: "Desktop productivity",
    status: "ready",
    recent: "18 分钟前",
    readiness: { connection: "ready", knowledge: "ready", ai: "ready" },
    connection: { workspace: "G:/TK-OPS/focus", browser: "Chrome Focus", environment: "本机 Runtime" },
    recipe: { id: "recipe-calm", name: "安静桌面", script: "GPT-5.4 mini", visual: "参考图增强", video: "Kling I2V", voice: "Calm EN", ratio: "9:16", inheritance: "系统默认" },
  },
  {
    id: "draft-demo",
    initials: "新",
    name: "新账号草稿",
    platform: "TikTok",
    positioning: "定位信息尚未完成",
    shortPositioning: "待配置",
    status: "draft",
    recent: "今天",
    readiness: { connection: "idle", knowledge: "idle", ai: "idle" },
    connection: {},
    recipe: null,
  },
  {
    id: "attention-demo",
    initials: "潮",
    name: "潮流观察室",
    platform: "TikTok",
    positioning: "全球创意硬件与设计趋势",
    shortPositioning: "创意硬件趋势",
    status: "attention",
    recent: "2 小时前",
    readiness: { connection: "ready", knowledge: "warning", ai: "error" },
    connection: { workspace: "G:/TK-OPS/trends", browser: "未检查", environment: "本机 Runtime" },
    recipe: { id: "recipe-image", name: "素材增强", script: "GPT-5.4 mini", visual: "Flux 参考图", video: "已下线模型", voice: "清亮中性", ratio: "9:16", inheritance: "账号覆盖 1 项" },
  },
  {
    id: "unbound-demo",
    initials: "评",
    name: "测评官小张",
    platform: "TikTok",
    positioning: "桌面硬件真实体验与长期测评",
    shortPositioning: "桌面硬件测评",
    status: "unbound",
    recent: "昨天",
    readiness: { connection: "warning", knowledge: "ready", ai: "ready" },
    connection: { workspace: "G:/TK-OPS/review", browser: "未绑定", environment: "本机 Runtime" },
    recipe: { id: "recipe-talk", name: "清晰口播", script: "GPT-5.4 mini", visual: "Flux 快速图", video: "Seedance Lite", voice: "清亮中性", ratio: "9:16", inheritance: "系统默认" },
  },
  {
    id: "archive-demo",
    initials: "旧",
    name: "旧测试账号",
    platform: "TikTok",
    positioning: "历史流程验证",
    shortPositioning: "历史测试",
    status: "archived",
    recent: "1 个月前",
    readiness: { connection: "idle", knowledge: "idle", ai: "idle" },
    connection: {},
    recipe: null,
  },
];

export const accountCopyFields = ["定位模板", "知识规则结构", "AI Recipe", "发布默认值"];
export const accountExcludedFields = ["授权与密钥", "设备绑定", "内容与索引", "任务与发布历史"];

export function cloneAccountProfiles() {
  return structuredClone(accountProfiles);
}

export function createCopiedDraft(source, id) {
  return {
    ...structuredClone(source),
    id,
    initials: "副",
    name: `${source.name} 副本`,
    status: "draft",
    recent: "刚刚",
    readiness: { connection: "idle", knowledge: "idle", ai: source.recipe ? "ready" : "idle" },
    connection: {},
  };
}
