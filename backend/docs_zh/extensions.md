
# 扩展

SillyTavern 附带了许多扩展，可以在扩展面板中启用或禁用。扩展可以添加新功能、改变现有功能的行为，或为你的 AI 提供额外内容。更多扩展可以从扩展面板的“下载扩展与资源”菜单中安装。

## 扩展面板

要打开或关闭扩展面板，请选择顶部栏中的 **<i class="fa-solid fa-cubes fa-fw"></i> 扩展**。

- **<i class="fa-solid fa-cubes"></i> 管理扩展**：激活、停用和更新扩展
- **下载扩展与资源**：从 SillyTavern 仓库安装[更多扩展](#可安装扩展)、角色、音效和背景
- **扩展更新时通知**：勾选后，当已安装扩展有可用更新时会收到通知
- **<i class="fa-solid fa-cloud-arrow-down"></i> 安装扩展**：从 Git 仓库 URL 导入[第三方扩展](#第三方扩展)

## 内置扩展

这些扩展内置于 SillyTavern，无需安装。可以在扩展面板中启用或禁用。

> **聊天翻译**
>
> 将聊天消息翻译成不同语言
> > **📝 提示**
>

**[图像描述](/extensions/captioning/)**

从图像生成文本，使你的 AI 能够“看到”并响应对话中的视觉内容
> **📝 提示**

> **[图像生成](/extensions/stable-diffusion/)**
>
> 使用本地或基于云的 Stable Diffusion、FLUX 或 DALL-E API 生成图像
> > **📝 提示**
>

**[表情图像](/extensions/expression-images/)**

AI 角色的图像（亦称“精灵图”），显示在聊天窗口旁边或后面
> **📝 提示**

> **[摘要](/extensions/summarize/)**
>
> 聊天历史的自动摘要
> > **📝 提示**
>

**[聊天向量化](/extensions/chat-vectorization/)**

从聊天历史中查找相关消息并将其添加到上下文中
> **📝 提示**

> **[文本转语音](/extensions/tts/)**
>
> 通过 ElevenLabs、Silero、系统 TTS、**[AllTalk](/extensions/alltalk/)**、**[XTTS](/extensions/xtts/)** 等为聊天消息提供语音朗读
> > **📝 提示**
>

**[快速回复](/usage/st-script/#快速回复脚本库与自动执行)**

一键回复聊天消息、运行命令和 STscript 等
> **📝 提示**

> **令牌计数器**
>
> 将文本转换为令牌并计算令牌数量
> > **📝 提示**
>
> ---
>
> ## 可安装扩展
>
> > **💡 Tip**
> >
> > 你**必须**安装了 Git 才能下载扩展。如果没有安装，请按照 [Git 安装页面](https://git-scm.com/downloads) 上的说明操作。
>
>
> 你可以直接在应用内浏览所有可用扩展列表，方法是进入 **<i class="fa-solid fa-cubes"></i> 扩展** => **下载扩展与资源** 菜单，点击 **<i class="fa-solid fa-plug-circle-exclamation"></i> 加载资源列表** 按钮。要安装扩展，请点击 **<i class="fa-solid fa-download"></i> 下载** 按钮。要了解更多扩展信息，请点击名称旁边的 **<i class="fa-solid fa-arrow-up-right-from-square"></i> 链接** 按钮打开其 GitHub 页面。
>
> > **ℹ️ 扩展并非 Extras**
> >
> > Extras 项目已于 2024 年 4 月停止。你不需要安装 Extras 来使用扩展。
>
>

**[Blip](/extensions/blip/)**

以可变速度动画显示角色消息的文本，并在动画期间播放音效。
> **📝 提示**

> **[动态音频](/extensions/dynamic-audio/)**
>
> 为你的聊天添加沉浸式背景音乐和环境音效。
> > **📝 提示**
>

**[EmulatorJS](/extensions/emulatorjs/)**

在 SillyTavern 聊天中直接玩复古主机游戏。
> **📝 提示**

> **[Live2d](/extensions/live2d/)**
>
> 增加对 live2d 模型的支持。可自定义的表情、动画和交互。
> > **📝 提示**
>

**目标**

为 AI 设定一个在聊天过程中努力达成的目标。
> **📝 提示**

> **[RVC](/extensions/rvc/)**
>
> 为文本转语音模块增加实时语音克隆能力。
> > **📝 提示**
>

**[语音识别](/extensions/speech-recognition/)**

使用浏览器或 extras 将语音转换为文本。
> **📝 提示**

> **[VRM](/extensions/vrm/)**
>
> 增加对 VRM 模型的支持。可自定义的表情、动画和交互。
> > **📝 提示**
>

**[网页搜索](/extensions/websearch/)**

将网页搜索结果添加到 LLM 提示中。
> **📝 提示**

> **[天气](https://github.com/SillyTavern/Extension-Weather)**
>
> 使用可用的天气 API 之一，通过斜杠命令或功能工具提供天气信息。
> > **📝 提示**
>

**[聊天顶部栏](https://github.com/SillyTavern/Extension-TopInfoBar)**

在聊天窗口顶部添加一个包含快捷操作快捷键的栏。
> **📝 提示**

> **[国际象棋](https://github.com/SillyTavern/SillyTavern-Chess)**
>
> 与 LLM 对弈国际象棋。
> > **📝 提示**
>

**[代码运行器](https://github.com/SillyTavern/Extension-CodeRunner)**

允许在聊天中的代码块里运行 JavaScript 和 STscript 代码。
> **📝 提示**

> **[D&D 骰子](https://github.com/SillyTavern/Extension-Dice)**
>
> 一套 7 个经典 D&D 骰子，满足所有投骰需求。
> > **📝 提示**
>

**[重复查找器](https://github.com/SillyTavern/Extension-DupeFinder)**

增加按相似度分组聚类角色的功能，便于查找重复角色。
> **📝 提示**

> **[表情选择器](https://github.com/SillyTavern/Extension-EmojiPicker)**
>
> 添加一个按钮，用于快速在聊天消息中插入表情符号。
> > **📝 提示**
>

**[群组问候语](https://github.com/SillyTavern/Extension-GroupGreetings)**

允许设置特定于群组聊天的替代问候语。
> **📝 提示**

> **[群组代发](https://github.com/SillyTavern/SillyTavern-GroupSendAs)**
>
> 添加一个按钮，用于快速插入所选群组成员的 /sendas 命令模板。
> > **📝 提示**
>

**[HypeBot](https://github.com/SillyTavern/Extension-HypeBot)**

使用 NovelAI 的 HypeBot 引擎，根据你最近的聊天显示个性化建议。需要有效的 NovelAI 订阅。
> **📝 提示**

> **[空闲](https://github.com/SillyTavern/Extension-Idle)**
>
> 在用户空闲一段时间后添加“空闲提示”，以自然方式继续对话。
> > **📝 提示**
>

**[图像元数据查看器](https://github.com/SillyTavern/Extension-ImageMetadataViewer)**

查看聊天中附加的放大图像的元数据。
> **📝 提示**

> **[LaTeX](https://github.com/SillyTavern/Extension-LaTeX)**
>
> 在聊天消息中渲染 LaTeX 和 AsciiMath 公式。
> > **📝 提示**
>

**[Mermaid](https://github.com/SillyTavern/Extension-Mermaid)**

在 SillyTavern 聊天中添加 Mermaid 图表和流程图渲染。
> **📝 提示**

> **[笔记本](https://github.com/SillyTavern/Extension-Notebook)**
>
> 添加一个存储笔记的地方。支持富文本格式。
> > **📝 提示**
>

**[参数随机化器](https://github.com/SillyTavern/Extension-Randomizer)**

每次生成时随机化 API 设置滑块的值。
> **📝 提示**

> **[Prome 视觉小说扩展](https://github.com/Bronya-Rand/Prome-VN-Extension)**
>
> 通过更多功能（专注模式、信箱模式等）增强当前视觉小说体验！
> > **📝 提示**
>

**[提示检查器](https://github.com/SillyTavern/Extension-PromptInspector)**

添加一个选项，在发送到服务器之前检查和编辑输出提示。
> **📝 提示**

> **[推送通知](https://github.com/SillyTavern/SillyTavern-PushNotifications)**
>
> 允许接收传入聊天消息的推送通知。
> > **📝 提示**
>

**[快速角色](https://github.com/SillyTavern/Extension-QuickPersona)**

在聊天栏中添加一个下拉菜单，用于选择用户角色。
> **📝 提示**

> **[RSS](https://github.com/SillyTavern/Extension-RSS)**
>
> 作为斜杠命令或功能工具，获取 RSS 订阅源的最新新闻。
> > **📝 提示**
>

**[屏幕共享](https://github.com/SillyTavern/Extension-ScreenShare)**

当你发送消息时，为多模态模型提供屏幕图像。
> **📝 提示**

> **[静音播放器](https://github.com/SillyTavern/Extension-Silence)**
>
> 在扩展菜单中添加一个静音音频播放器。如果浏览器标签页在后台被杀死，可能有所帮助。
> > **📝 提示**
>

**[时间线](https://github.com/SillyTavern/SillyTavern-Timelines)**

为聊天历史添加时间线导航。
> **📝 提示**

> **[变量查看器](https://github.com/LenAnderson/SillyTavern-Variable-Viewer)**
>
> 轻松查看和修改变量的方式。
> > **📝 提示**
>

**[WebLLM](https://github.com/SillyTavern/Extension-WebLLM)**

为扩展提供接口，使其可以借助内嵌到浏览器的语言模型来推理。此扩展本身不提供模型或 UI，仅用作供其他扩展使用的依赖库。

> [!TIP]
> 此扩展是为开发者设计的，**不能**作为聊天后端使用。它供其他扩展间接使用。
> **📝 提示**

## 第三方扩展

> **🚫 Danger**
>
> 使用第三方扩展可能会产生意外副作用，并可能带来安全风险。
> 在通过 **<i class="fa-solid fa-cloud-arrow-down"></i> 安装扩展** 导入扩展之前，请务必确保你信任该来源。
> 我们对第三方扩展造成的任何损害概不负责。


要安装第三方扩展，请进入 **<i class="fa-solid fa-cubes"></i> 扩展** => **<i class="fa-solid fa-cloud-arrow-down"></i> 安装扩展** 菜单，粘贴扩展仓库的 URL。可选地，指定分支和（在[多用户](/administration/multi-user/)场景下）安装目标：所有用户或仅当前用户。扩展将自动下载并加载。