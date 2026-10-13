
# TTS

SillyTavern 提供了多种 TTS（文本转语音）选项，可用于让语音朗读聊天内容的部分内容。本页说明其设置和使用。

## 配置 TTS

### TTS 提供商选择

用于选择您想使用的 TTS 服务。部分选项免费，部分需要付费订阅，还有一些在您的 PC 上本地运行。

可用选项（列表可能随时间变化）：

- **AllTalk** - 免费、开源本地安装，提供多种 TTS 引擎。请参阅 [AllTalk](/extensions/alltalk/) 页面了解设置说明。
- **Azure TTS** - 与 Microsoft Edge 相同的语音。需要 Azure 账户和付费订阅。
- **Coqui-TTS**（已弃用） - 免费，需要 Extras API 运行。高性能文本转语音模型（Tacotron、Tacotron2、Glow-TTS、SpeedySpeech）以及 Bark。
- **Edge** - 免费，通过 Azure 运行。当选择“Plugin”作为提供商时，您还需要安装[此服务器插件](https://github.com/SillyTavern/SillyTavern-EdgeTTS-Plugin)。另一种选项需要 Extras API（已弃用）运行。
- **Electron Hub** - 重复使用您的 [Electron Hub](https://electronhub.ai/) API 密钥，以按模型控制访问云端语音（GPT-4o Mini TTS、Microsoft 神经语音等）。
- **ElevenLabs** - 需要付费订阅。从 [ElevenLabs](https://elevenlabs.io/) 获取 API 密钥。
- **Google Translate** - Google 提供的免费语音，每种语言一个，质量差异可能很大。
- **Google Gemini TTS** - 需要从 [Vertex AI](/usage/api-connections/google/#google-vertex-ai) 或 [AI Studio](/usage/api-connections/google/#google-ai-studio) 获取 API 密钥，使用 [Gemini TTS](https://cloud.google.com/text-to-speech/docs/gemini-tts) 模型。
- **Kokoro** - 免费，使用 [kokoro.js](https://www.npmjs.com/package/kokoro-js) 在浏览器本地运行模型。然而，[某些浏览器](https://caniuse.com/webgpu) 可能不支持设备选项所需的 WebGPU。
- **MiniMax** - 需要从 [MiniMax](https://www.minimax.io/) 获取 API 密钥。请参阅 [MiniMax TTS](/extensions/minimaxtts/) 页面了解设置说明。
- **Novel** - 需要付费的 NovelAI 订阅，由 NovelAI 的 TTS 引擎生成。
- **OpenAI** - 需要付费 API 密钥，使用 OpenAI 的 TTS 模型。
- **Pollinations** - 免费访问 OpenAI TTS 模型，但有速率限制。[网站](https://pollinations.ai/)。
- **Silero** - 免费，在您的 PC 上运行，质量差异可能很大。需要安装[专用 API 服务器](https://github.com/ouoertheo/silero-api-server) 或 Extras API（已弃用）。
- **System** - 使用您的操作系统 TTS 引擎（如果存在）。质量因操作系统而异，可能差异很大。
- **XTTS** - 免费，需要安装专用 API 服务器。请参阅 [XTTS](/extensions/xtts/) 页面了解设置说明。

### 复选框

- **启用** - 打开/关闭 TTS 播放
- **自动生成** - 当新消息进入聊天时，让 TTS 自动开始播放
- **仅朗读“引号”** - 将 TTS 播放限制为仅包含在 `"引号"` 内的文本。这将包含 `*星号行中的 "引号"*`（内部变量名 = `narrate_quoted_only`）
- **忽略星号内的 \*文本，甚至 "引号"\*** - TTS 不会播放 `*星号*` 内的任何文本，即使有 "引号"（内部变量名 = `narrate_dialogues_only`）
- *同时勾选“仅朗读引号”和“忽略星号”复选框将导致 TTS 只读取不在星号中的 "引号"，并忽略其他所有内容。*
- **仅朗读翻译后的文本** - 这将使 TTS 仅朗读翻译后的文本。
- **应用正则表达式** - 在将文本发送到 TTS 提供商之前，将提供的正则表达式模式应用于文本。用于移除输入文本中不需要的部分，例如表情符号或 TTS 引擎处理不佳的非母语字符。

给定示例文本：`*Cohee approaches you with a faint "nya"* "Good evening, senpai", she says.`
下面是一个表格，显示根据 **忽略星号内的 \*文本，甚至 "引号"\*** 和 **仅朗读 "引号"** 的布尔状态，文本将如何修改：

| **忽略星号内的 \*文本，甚至 "引号"\*** | **仅朗读 "引号"** | **输出**                                                                |
|:---------------------------------------|:------------------|:------------------------------------------------------------------------| 
| 禁用                                   | 禁用              | Cohee approaches you with a faint "nya" "Good evening, senpai", she says. |
| 禁用                                   | 启用              | "nya"... "Good evening, senpai"                                           |
| 启用                                   | 禁用              | "Good evening, senpai", she says.                                         |
| 启用                                   | 启用              | "Good evening, senpai"                                                    |

### 滑块

这些会根据您选择的 API 而变化。

### 按钮

- **应用** - 设置 TTS API 并编辑语音映射后，必须点击此按钮。
- **刷新** - 从选定的 TTS API 重新加载语音列表。
- **可用语音** - 加载一个弹出窗口，显示所选 API 的所有可用语音，并允许您通过示例对话预览它们。

## 使用 TTS

1. 点击“启用”复选框，否则不会发生任何事情。
2. 如果您希望每次新消息到达聊天时 TTS 自动开始，请点击“自动生成”复选框。
3. 可选地，点击任何消息右上角的扩音器图标以按需播放。
4. 点击右下角的“停止”按钮（位于魔棒菜单内）以停止任何播放。

### 语音映射

您必须为 TTS 提供语音映射，否则它将不知道每个角色应使用哪些语音。要设置语音映射，首先打开一个您想为其分配语音的角色的聊天，和/或选择一个用户角色以分配语音，然后从下拉列表中选择一个由 TTS 提供商列出的语音。如果没有看到语音和/或角色列表，请确保您的 TTS 提供商配置正确，然后点击“刷新”。某些提供商（如 OpenAI 兼容或 NovelAI）需要您手动填充语音列表。