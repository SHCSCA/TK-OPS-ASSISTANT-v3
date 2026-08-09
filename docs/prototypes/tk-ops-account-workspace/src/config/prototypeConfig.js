export const prototypeConfig = Object.freeze({
  accountSwitchDelay: 520,
  actionDelay: 720,
  ai: {
    defaultRecipeId: "recipe-talk",
    providerTestDelay: 720,
    modelDiscoveryDelay: 680,
    adapterTypes: [
      { id: "openai-compatible", label: "OpenAI Compatible", defaultBaseUrl: "https://api.example.com/v1", timeoutSeconds: 90 },
      { id: "comfyui", label: "ComfyUI", defaultBaseUrl: "http://127.0.0.1:8188", timeoutSeconds: 600 },
      { id: "runninghub", label: "RunningHub", defaultBaseUrl: "https://www.runninghub.ai", timeoutSeconds: 900 },
    ],
    capabilityIds: ["text-generation", "structured-output", "vision-analysis", "text-to-image", "image-to-video", "text-to-video", "tts"],
  },
  content: {
    suggestionCount: 3,
    targetDurations: [15, 30, 45, 60],
  },
  library: {
    defaultSort: "latest",
    defaultType: "all",
  },
  production: {
    appendableStages: ["选题", "脚本", "分镜", "排队", "生成", "合成"],
    scriptSplitModes: [
      { id: "paragraph", label: "按段落拆分", hint: "一个自然段生成一个视频单元" },
      { id: "line", label: "按行拆分", hint: "每个非空行生成一个视频单元" },
      { id: "sentence", label: "按句子拆分", hint: "按句号、问号或感叹号划分视频" },
    ],
  },
  appName: "TK-OPS",
  demoLabel: "演示原型",
  runtimeVersion: "Prototype Runtime",
  stageOrder: ["选题", "脚本", "分镜", "生成", "合成", "待发布"],
  storageKeys: {
    theme: "tkops-prototype-theme",
  },
});
