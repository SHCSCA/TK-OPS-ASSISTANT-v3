import type {
  KnowledgeKind,
  KnowledgeSourceStatus
} from "@/types/runtime/account-knowledge";

export const sourceStatusLabels: Record<KnowledgeSourceStatus, string> = {
  pending: "待索引",
  indexing: "索引中",
  ready: "可用",
  failed: "失败",
  stale: "需重建",
  removed: "已移除"
};

export const sourceKindLabels: Record<KnowledgeKind, string> = {
  document: "文档",
  image: "图片",
  video: "视频",
  audio: "音频",
  text: "文本",
  reference: "网址"
};

export function formatKnowledgeDate(value: string | null): string {
  if (!value) return "尚未发生";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

export function objectItemCount(value: Record<string, unknown>): number {
  return Object.keys(value).length;
}
