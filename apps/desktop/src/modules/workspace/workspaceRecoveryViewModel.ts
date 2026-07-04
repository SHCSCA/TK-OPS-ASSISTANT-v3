import type { WorkspaceAssemblySourceDto, WorkspaceAssemblyStateDto } from "@/types/runtime";

export interface WorkspaceRecoverySource {
  kind: string;
  label: string;
  message: string;
}

export interface WorkspaceSourceRecoveryViewModel {
  heading: string;
  message: string;
  nextStep: string;
  showTtsSettingsAction: boolean;
  showVoiceAction: boolean;
  sources: WorkspaceRecoverySource[];
  statusLabel: string;
  visible: boolean;
}

const emptySourceRecovery: WorkspaceSourceRecoveryViewModel = {
  heading: "",
  message: "",
  nextStep: "",
  showTtsSettingsAction: false,
  showVoiceAction: false,
  sources: [],
  statusLabel: "",
  visible: false
};

export function buildRecoverySources(
  sources: WorkspaceAssemblySourceDto[]
): WorkspaceRecoverySource[] {
  return sources
    .filter((source) => source.status !== "ready" || source.segmentCount <= 0)
    .map((source) => ({
      kind: source.kind,
      label: source.label || sourceKindLabel(source.kind),
      message: source.message || `${sourceKindLabel(source.kind)}尚未就绪。`
    }));
}

export function buildSourceRecoveryViewModel(options: {
  assemblyState: WorkspaceAssemblyStateDto | null;
  hasTimeline: boolean;
  trackCount: number;
}): WorkspaceSourceRecoveryViewModel {
  const { assemblyState, hasTimeline, trackCount } = options;
  if (!assemblyState || assemblyState.status === "ready") {
    return emptySourceRecovery;
  }

  const sources = buildRecoverySources(assemblyState.sources);
  const issueMessage = assemblyState.issues.join(" ");
  if (sources.length === 0 && issueMessage.length === 0) {
    return emptySourceRecovery;
  }

  const sourceNames = sources.length > 0
    ? sources.map((source) => source.label).join("、")
    : "脚本文案、分镜规划、配音轨或字幕轨";
  const zeroTrackMessage = hasTimeline && trackCount === 0
    ? " 当前时间线显示 0 轨，是因为真实来源未补齐，不是同步按钮无效。"
    : "";
  const reason = issueMessage || `缺少${sourceNames}，无法生成完整 AI 三轨。`;
  const voiceOnlyMissing = sources.length === 1 && sources[0]?.kind === "voice";
  const voiceIssue = voiceOnlyMissing || /TTS|Provider|缺少可用配音轨|配音轨不可用/i.test(issueMessage);

  return {
    heading: voiceIssue ? "缺少配音轨" : "缺少创作来源",
    message: `${reason}${zeroTrackMessage}`,
    nextStep: voiceIssue
      ? "下一步可先完成配音或配置 TTS 能力，再回到工作台重新同步 AI 三轨。"
      : "下一步应先完成脚本、分镜、配音和字幕，再回到工作台重新同步 AI 三轨。",
    showTtsSettingsAction: voiceIssue,
    showVoiceAction: voiceIssue,
    sources,
    statusLabel: assemblyState.status === "blocked" ? "已阻断" : "需补齐",
    visible: true
  };
}

function sourceKindLabel(kind: string): string {
  if (kind === "script") return "脚本文案";
  if (kind === "storyboard") return "分镜规划";
  if (kind === "voice") return "配音轨";
  if (kind === "subtitle") return "字幕轨";
  return kind;
}
