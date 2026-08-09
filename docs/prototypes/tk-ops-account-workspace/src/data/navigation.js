import {
  IconBooks,
  IconChartDots3,
  IconFileText,
  IconHierarchy3,
  IconLayoutDashboard,
  IconMovie,
  IconPackages,
  IconRocket,
  IconTool,
  IconTargetArrow,
} from "@tabler/icons-react";

export const navigationItems = [
  { id: "workspace", label: "工作台", icon: IconLayoutDashboard },
  { id: "knowledge", label: "定位与知识", icon: IconTargetArrow },
  { id: "scripts", label: "脚本与选题", icon: IconFileText, group: "creative" },
  { id: "storyboard", label: "分镜规划", icon: IconHierarchy3, group: "creative" },
  { id: "deconstruction", label: "视频拆解", icon: IconMovie, group: "creative" },
  { id: "production", label: "批量生产", icon: IconPackages, group: "creative" },
  { id: "library", label: "内容库", icon: IconBooks, group: "delivery" },
  { id: "toolbox", label: "媒体工具箱", icon: IconTool, group: "delivery" },
  { id: "publishing", label: "发布", icon: IconRocket, group: "delivery" },
  { id: "review", label: "复盘", icon: IconChartDots3, group: "delivery" },
];
