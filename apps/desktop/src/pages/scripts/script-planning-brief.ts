export type ScriptPlanningBrief = {
  accountPositioning: string;
  duration: string;
  forbiddenContent: string;
  languageRequirement: string;
  productService: string;
  shootingConditions: string;
  targetUsers: string;
  videoGoal: string;
  videoStyle: string;
  videoTheme: string;
};

export type PlanningSelectFieldKey =
  | "accountPositioning"
  | "duration"
  | "languageRequirement"
  | "shootingConditions"
  | "videoGoal"
  | "videoStyle";

export type PlanningTextFieldKey = "forbiddenContent" | "productService" | "targetUsers" | "videoTheme";

export const planningSelectOptions: Record<PlanningSelectFieldKey, string[]> = {
  accountPositioning: ["测评号", "剧情号", "种草号", "专业科普号", "工厂号", "品牌号", "个人IP号"],
  duration: ["15秒", "30秒", "45秒", "60秒"],
  languageRequirement: ["中文", "英文", "中英双语"],
  shootingConditions: ["真人出镜", "不露脸", "产品实拍", "手部演示", "图文混剪", "AI视频", "工厂实拍"],
  videoGoal: ["涨粉", "引流", "带货", "种草", "品牌曝光", "评论互动", "私信转化"],
  videoStyle: ["真实口播", "剧情反转", "测评对比", "痛点放大", "情绪共鸣", "搞笑夸张", "高级质感", "街头采访"]
};

const planningLabels: Record<keyof ScriptPlanningBrief, string> = {
  accountPositioning: "账号定位",
  duration: "视频时长",
  forbiddenContent: "禁止内容",
  languageRequirement: "语言要求",
  productService: "产品/服务",
  shootingConditions: "拍摄条件",
  targetUsers: "目标用户",
  videoGoal: "视频目的",
  videoStyle: "视频风格",
  videoTheme: "视频主题"
};

const promptFieldOrder: Array<keyof ScriptPlanningBrief> = [
  "videoTheme",
  "productService",
  "targetUsers",
  "videoGoal",
  "duration",
  "accountPositioning",
  "videoStyle",
  "shootingConditions",
  "languageRequirement",
  "forbiddenContent"
];

export function createDefaultPlanningBrief(): ScriptPlanningBrief {
  return {
    accountPositioning: "",
    duration: "",
    forbiddenContent: "",
    languageRequirement: "",
    productService: "无",
    shootingConditions: "",
    targetUsers: "",
    videoGoal: "",
    videoStyle: "",
    videoTheme: ""
  };
}

export function buildScriptPlanningPrompt(brief: ScriptPlanningBrief): string {
  const lines = [
    "请根据以下策划信息生成 TikTok 短视频脚本。",
    "",
    ...promptFieldOrder.map((key) => `${planningLabels[key]}：${normalizeFieldValue(brief[key])}`),
    "",
    "输出要求：",
    "- 请输出 Markdown 格式脚本。",
    "- 至少包含脚本标题、核心卖点、分镜脚本表格、拍摄提示和结尾转化动作。",
    "- 分镜脚本表格建议包含时间点、画面内容、镜头/机位、字幕/台词、动作、音效/音乐。",
    "- 不要输出外层 ```markdown 代码围栏。"
  ];
  return lines.join("\n");
}

export function getPlanningFieldLabel(key: keyof ScriptPlanningBrief): string {
  return planningLabels[key];
}

function normalizeFieldValue(value: string): string {
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : "未填写";
}
