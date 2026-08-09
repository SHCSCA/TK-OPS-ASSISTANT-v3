export const capabilityRoutes = [
  route("topic-suggest", "选题推荐", "gpt-5.4-mini", null, "prompt-script-1"),
  route("script-generate", "脚本生成", "gpt-5.4-mini", null, "prompt-script-1"),
  route("script-improve", "脚本优化", "gpt-5.4-mini", null, "prompt-script-1"),
  route("storyboard", "分镜规划", "gpt-5.4-mini", null, "prompt-storyboard-1"),
  route("deconstruction", "视频拆解", "gpt-5.4-mini", null, "prompt-deconstruction-1"),
  route("transcription", "语音转写", null, null, null),
  route("text-to-image", "文生图", "flux-dev", null, "prompt-visual-1"),
  route("text-to-video", "文生视频", null, "rh-video", "prompt-visual-1"),
  route("image-to-video", "图生视频", "wan-i2v", null, "prompt-visual-1"),
  route("tts", "TTS", "local-tts", null, null),
  route("subtitle", "字幕对齐", null, null, null),
  route("embedding", "Embedding", null, null, null),
];

export function cloneCapabilityRoutes() {
  return structuredClone(capabilityRoutes);
}

function route(id, label, primaryModelProfileId, fallbackModelProfileId, promptProfileId) {
  return { id, label, primaryModelProfileId, fallbackModelProfileId, promptProfileId, source: "系统默认" };
}
