# AllTalk TTS V2

AllTalk 是一款基于 Coqui XTTS、F5-TTS、VITS、Piper 及其他 TTS 模型引擎的语音克隆系统，旨在生成高质量的语音复刻（支持零样本语音克隆或内置语音）。在 AllTalk V2 中，重要更新增强了功能并简化了使用，包括多 TTS 引擎支持、扩展的自定义选项以及性能优化。完整的功能列表请参考 [AllTalk Wiki](https://github.com/erew123/alltalk_tts/wiki)。

---

## 🟩 AllTalk V2 核心功能
- **多引擎支持**：轻松切换 Coqui XTTS、VITS、Piper、Parler、F5 及自定义引擎。
- **语音转换（RVC）**：增强的基于检索的语音克隆流水线。
- **可自定义设置**：按引擎调整设置并保存启动配置。
- **旁白功能**：为旁白和角色分别指定语音。
- **独立与集成使用**：与 SillyTavern 无缝集成。
- **DeepSpeed 与低显存模式**：针对资源受限环境的性能优化。
- **截图**：查看 AllTalk V2 界面，请点击[此处](https://github.com/erew123/alltalk_tts/discussions/237)。

---

## 🟨 安装与设置选项

AllTalk 提供独立安装和集成安装两种方式。最快的方式是使用提供的快速安装选项，脚本可自动化大部分流程。

- **独立安装**：推荐大多数用户使用（[独立安装指南](https://github.com/erew123/alltalk_tts/wiki/Install-%E2%80%90-Standalone-Installation)）
- **Text-generation-webui 集成**：集成到 Text-generation-webui 中（[TGWUI 安装指南](https://github.com/erew123/alltalk_tts/wiki/Install-%E2%80%90-Text%E2%80%90generation%E2%80%90webui-Installation)）

#### 🟩 自动安装
**此方法仅适用于 Windows 用户。**
对于希望快速设置的新用户，自动安装使用 SillyTavern-Launcher。
注意：此方法假定您已安装 SillyTavern-Launcher。如果尚未安装，请访问 https://github.com/SillyTavern/SillyTavern-Launcher 并按照 readme.md 文件中的说明进行安装。
安装 SillyTavern-Launcher 后：
1. 运行 Launcher.bat
2. 转到：`Home > Toolbox > App Installer > Voice Generation`
3. 选择标记为：**Install AllTalk V2** 的选项

#### 🟩 手动安装
对于需要详细控制的高级用户，请遵循[手动安装指南](https://github.com/erew123/alltalk_tts/wiki/Install-%E2%80%90-Manual-Installation-Guide)在 Windows、Linux 或 Mac（未经测试）上逐步安装。

#### 🟩 Google Colab 安装
对于不希望本地安装的用户，可在云端环境中运行 AllTalk，请参考 [Google Colab 安装指南](https://github.com/erew123/alltalk_tts/wiki/Google-COLAB)。

---

## 🟨 在 SillyTavern 中使用 AllTalk

加载 AllTalk 后，在 SillyTavern 的 TTS 页面中选择 AllTalk，并确保在设置中选择正确的 AllTalk 服务器版本。

- **设置管理**：AllTalk 可能会根据您选择的配置启用或禁用特定设置。
- **加载顺序**：如果 SillyTavern 在 AllTalk 之前加载，请重新加载 TTS 扩展页面。
- **性能优化**：根据系统资源选择性启用 DeepSpeed 和低显存模式以提升性能。
- **旁白功能**：旁白功能的详细信息可在 [AllTalk Wiki](https://github.com/erew123/alltalk_tts/wiki/Narrator-Function) 中找到。

有关 SillyTavern AllTalk 扩展的完整详细信息，将在 [AllTalk Wiki 的 SillyTavern 页面](https://github.com/erew123/alltalk_tts/wiki/SillyTavern-Extension) 中更新。

使用 AllTalk 扩展的 TGWUI 用户需要在 TGWUI 聊天界面中禁用 `Enable TGWUI TTS`，否则会生成重复的 TTS 音频。

---

## 🟨 故障排除

如果您遇到认为与 SillyTavern 中 AllTalk 相关的问题，请参考 [AllTalk Wiki 的 SillyTavern 页面](https://github.com/erew123/alltalk_tts/wiki/SillyTavern-Extension) 获取最新信息。

---

### 🟪 支持、帮助与功能请求

如需进一步帮助：
- 参考 [Wiki](https://github.com/erew123/alltalk_tts/wiki) 及内置文档。
- 加入 [讨论板](https://github.com/erew123/alltalk_tts/discussions/245) 参与讨论。
- 通过 [问题追踪器](https://github.com/erew123/alltalk_tts/issues) 提交错误或功能请求。

---