export const emptyStateDefinitions = {
  workspace: { eyebrow: "从这里开始", title: "这个账号还没有创作任务", description: "先新建选题，或从固定脚本、素材与视频拆解进入创作。", actionLabel: "新建选题", actionId: "new-topic", secondaryLabel: "开始批量生产", secondaryActionId: "new-batch" },
  knowledge: { eyebrow: "账号独立知识库", title: "还没有可用的定位与知识", description: "先补齐账号定位，再导入文档、网页或历史内容。", actionLabel: "编辑定位", actionId: "edit-positioning", secondaryLabel: "导入资料", secondaryActionId: "import-knowledge" },
  scripts: { eyebrow: "单条创作链", title: "还没有选题", description: "创建第一个选题后，可继续生成脚本并联动到分镜。", actionLabel: "新建选题", actionId: "new-topic" },
  storyboard: { eyebrow: "等待上游内容", title: "还没有可规划的脚本", description: "分镜始终从已采用脚本开始，不会生成孤立镜头。", actionLabel: "前往脚本与选题", actionId: "go-scripts" },
  deconstruction: { eyebrow: "视频拆解", title: "还没有拆解任务", description: "导入你有权处理的视频，提取脚本、关键词、关键帧与内容结构。", actionLabel: "导入视频", actionId: "new-deconstruction" },
  production: { eyebrow: "批量生产", title: "还没有生产批次", description: "可从固定脚本、选题矩阵、素材或拆解结果创建批次。", actionLabel: "新建生产批次", actionId: "new-batch" },
  library: { eyebrow: "账号内容库", title: "内容库还是空的", description: "视频、图片、文档、音频与生成结果会统一归档在这里。", actionLabel: "导入内容", actionId: "import-content" },
  toolbox: { eyebrow: "媒体工具箱", title: "还没有处理任务", description: "选择下载、去水印或格式处理工具，结果会回到当前账号内容库。", actionLabel: "选择工具", actionId: "choose-tool" },
  publishing: { eyebrow: "发布中心", title: "还没有待发布内容", description: "生产完成并通过检查的视频会进入这里。", actionLabel: "前往批量生产", actionId: "go-production" },
  review: { eyebrow: "复盘与优化", title: "还没有复盘数据", description: "发布完成后再回到这里记录表现与下一轮改进。", actionLabel: "前往发布中心", actionId: "go-publishing" },
};
