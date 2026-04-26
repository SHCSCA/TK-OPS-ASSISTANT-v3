# 媒体工具内置说明

TK-OPS 使用 FFprobe 解析视频时长、分辨率和编码格式。项目不提交 `ffprobe.exe` 二进制文件，而是在构建前按需下载并校验。

## 准备命令

```powershell
npm --prefix apps/desktop run prepare:media-tools
```

脚本会检查：

```text
apps/desktop/src-tauri/resources/bin/ffprobe/windows-x64/ffprobe.exe
```

如果文件存在且 SHA256 匹配，会直接跳过下载；如果不存在或校验失败，会下载固定版本的 LGPL Windows x64 构建包，解压 `ffprobe.exe` 并再次校验。

## 默认来源

- 来源：BtbN FFmpeg-Builds GitHub Releases
- 包名：`ffmpeg-n7.1.3-35-g419cdf9dcc-win64-lgpl-shared-7.1.zip`
- Archive SHA256：`270D2DED388676913408874AC015600861F267732D7C083093B03479B0803EAC`
- FFprobe SHA256：`A7C5CE012983EA485C2709CE705F24FA93FF95E462C04B30F4AE74461847CE41`

## Runtime 查找顺序

1. `TK_OPS_FFPROBE_PATH`
2. `TK_OPS_RESOURCE_DIR/bin/ffprobe/windows-x64/ffprobe.exe`
3. 开发态 `apps/desktop/src-tauri/resources/bin/ffprobe/windows-x64/ffprobe.exe`
4. 系统 PATH 中的 `ffprobe`
5. MP4/MOV 基础降级解析

## 注意

- `ffprobe.exe` 不进入 Git。
- 打包前需要先执行准备命令，Tauri build 已配置自动执行。
- 若下载源不可用，脚本会失败并输出中文错误，避免带着不完整媒体工具继续打包。
