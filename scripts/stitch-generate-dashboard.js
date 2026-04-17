const { spawnSync } = require("node:child_process");
const data = { 
    projectId: "7613239389915091327", 
    deviceType: "DESKTOP", 
    prompt: "TK-OPS 仪表盘主页，桌面端结构：Title Bar, Sidebar, Content Host, Detail Panel, Status Bar。视觉方向：本地 AI 视频创作指挥舱、低噪声、高层级、少量玻璃/磨砂层次、清晰状态反馈。主内容区域显示项目列表和实时渲染进度，侧边栏显示导航项（账号、素材、自动化、仪表盘、设备、发布、渲染、评审、脚本、设置、配置、分镜、字幕、视频、语音、工作区）。使用中文用户文案，保留技术词：Runtime、Provider、OpenAI。" 
};
const args = ["/d", "/s", "/c", "npx", "-y", "@_davideast/stitch-mcp", "tool", "generate_screen_from_text", "-d", JSON.stringify(data), "-o", "json"];
const result = spawnSync(process.env.ComSpec || "cmd.exe", args, { encoding: "utf8", maxBuffer: 1024 * 1024 * 20 });
process.stdout.write(result.stdout || "");
process.stderr.write(result.stderr || "");
process.exit(result.status ?? 1);
