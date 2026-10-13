
# 图像生成

使用本地或基于云的 Stable Diffusion、FLUX 或 DALL-E API 生成图像。

自动生成图像作为消息回复以实现完全沉浸式体验，
通过魔杖菜单或斜杠命令从聊天记录和角色信息生成，
或在聊天输入栏中使用 `/sd (anything_here)` 命令以你自己的提示词生成图像。

大多数常见的 Stable Diffusion 生成设置都可以在 SillyTavern UI 中自定义。

- 支持[多种图像生成来源](#supported-sources)，包括本地和基于云的
- 多种[生成模式](#generation-modes)，适用于角色、场景和自定义提示词
- [斜杠命令](#how-to-generate-an-image)可在聊天中轻松生成图像
- [交互模式](#use-interactive-mode)可根据自然语言请求触发图像生成
- 可自定义的提示词模板和[前缀](#common-prompt-prefix)，以保持一致的风格和质量
- [角色专属提示词前缀](#character-specific-prompt-prefix)，用于定制角色图像
- [风格预设](#styles)可快速切换不同的图像生成设置
- 灵活的[可见性选项](#chat-message-visibility)，控制生成图像在聊天中的显示
- 高级 [ComfyUI 集成](#comfyui-configuration)，实现高度可自定义的工作流
- 能够在角色图库中[查看所有生成的图像](#view-all-generated-images)
- [图像滑动切换](#image-swipes)功能，可在保持相同提示词的情况下重新生成图像
- 可[在生成前编辑提示词](#edit-prompts-before-generation)并[扩展自由模式提示词](#extend-free-mode-prompts)
- 与 AI [函数调用](#use-function-tool)集成，自动检测图像生成意图
  
## 支持的来源

| 来源                                                                                              | 备注                                                                                            |
|:--------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------|
| [AI/ML API](https://aimlapi.com/)                                                                 | 云端，付费                                                                                      |
| [Black Forest Labs](https://bfl.ai/)                                                              | 云端，付费                                                                                      |
| [Cloudflare Workers AI](https://www.cloudflare.com/developer-platform/products/workers-ai/)       | 云端，付费，多种具有视觉能力的模型                                                              |
| [Chutes](https://chutes.ai/)                                                                      | 云端                                                                                            |
| [ComfyUI](https://github.com/comfyanonymous/ComfyUI)                                              | 本地，开源（GPL3），免费，参见 [ComfyUI 配置](#comfyui-configuration)。                         |
| [Draw Things](https://drawthings.ai/)                                                             | 本地，Mac/iOS，免费                                                                             |
| [Electron Hub](https://electronhub.ai/)                                                           | 云端，付费                                                                                      |
| [FAL.AI](https://fal.ai/)                                                                         | 云端，付费                                                                                      |
| [Google AI Studio](https://aistudio.google.com/) / [Google Vertex AI](https://cloud.google.com/vertex-ai) | 云端，付费。Imagen 模型系列。AI Studio 支持的模型较少。                                  |
| [HuggingFace Serverless](https://huggingface.co/docs/api-inference/index)                         | 云端，免费                                                                                      |
| [NanoGPT](https://nano-gpt.com/)                                                                  | 云端，付费                                                                                      |
| [NovelAI Diffusion](https://novelai.net/)                                                         | 云端，需要有效订阅                                                                              |
| [OpenAI](https://platform.openai.com/)                                                            | 云端，付费                                                                                      |
| [OpenRouter](https://openrouter.ai/)                                                              | 云端                                                                                            |
| [Pollinations](https://pollinations.ai/)                                                          | 云端，开源（MIT），付费                                                                         |
| [SD.Next / vladmandic](https://github.com/vladmandic/automatic)                                   | 本地，开源（AGPL3），免费                                                                       |
| [SillyTavern Extras](https://github.com/SillyTavern/SillyTavern-Extras)                           | 已弃用，不推荐                                                                                  |
| [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp)                            | 本地，开源（MIT），免费                                                                         |
| [Stability AI](https://platform.stability.ai/)                                                    | 云端，付费                                                                                      |
| [Stable Diffusion WebUI / AUTOMATIC1111](https://github.com/AUTOMATIC1111/stable-diffusion-webui) | 本地，开源（AGPL3），免费                                                                       |
| [Stable Horde](https://stablehorde.net/)                                                          | 云端，开源（AGPL3），免费                                                                       |
| [TogetherAI](https://docs.together.ai/docs/serverless-models#image-models)                        | 云端                                                                                            |
| [x.AI](https://x.ai/)                                                                             | 云端，付费                                                                                      |
| [Z.AI](https://z.ai/)                                                                             | 云端，付费                                                                                      |

## 生成模式

| 魔杖菜单项         | 斜杠命令参数           | 描述                                           | 备注                                  |
|:-------------------|:-----------------------|:-----------------------------------------------|:--------------------------------------|
| "Yourself"         | `you`                  | 当前角色的全身肖像。                           | -                                     | 
| "Your Face"        | `face`                 | 当前角色的特写肖像。                           | 强制使用肖像宽高比。                  |
| "Me"               | `me`                   | 用户人设的肖像。                               | -                                     |
| "The Whole Story"  | `scene`                | 聊天事件的视觉回顾。                           | -                                     |
| "The Last Message" | `last`                 | 最后一条聊天消息的视觉回顾。                   | -                                     |
| "Raw Last Message" | `raw_last`             | 最后一条消息直接用作提示词。                   | -                                     |
| "Background"       | `background`           | 基于故事背景的聊天背景。                       | 强制使用宽幅横向宽高比。              |

## 如何生成图像

1. 使用扩展上下文菜单（魔杖）中的"图像生成"项。
2. 输入 `/sd (参数)` 斜杠命令，参数来自生成模式表。其他任何内容都会触发"自由模式"，让 SD 生成你提示的任何内容。例如：`/sd apple tree` 会生成一幅苹果树的图片。
3. 在聊天消息的上下文操作中查找画笔图标。这将为所选消息强制使用"原始消息"模式。

除原始消息和自由模式外，每种生成模式都会使用你当前选择的主生成 API 触发提示词生成，将聊天上下文转换为 SD 提示词。
你可以使用扩展面板中的"SD 提示词模板"设置抽屉，为每种生成模式配置生成提示词的指令模板。

### `/sd` 命令使用技巧

#### 查看所有生成的图像

要查看某个角色的所有已保存图像（包括其他聊天中的），请从角色信息面板的"更多..."下拉菜单中打开图库，或使用 `/show-gallery` 斜杠命令。

#### 指定负面提示词

在提示词前使用 `negative` 命名参数，为此生成强制指定特定的负面提示词。

```stscript
/sd negative="fries" cute tater farmer holding a tayto in a spud-field
```

#### 包含角色专属前缀

在自由提示词模式下使用特殊的 `{{charPrefix}}` 宏，以包含当前角色的正面和负面提示词前缀（如果已定义）。

```stscript
/sd {{charPrefix}}, riding a bike
```

#### 禁止发送聊天消息

你可以通过传递 `quiet=true` 命名参数来避免将生成的图像发送到聊天中。图像仍会被添加到角色图库中，命令将生成一个指向该图像的相对 URL，可供其他命令使用。

以下示例将以用户人设的身份使用 Markdown 发送生成的图像。

```stscript
/sd quiet=true me | /send Here's a picture of me: ![my portrait]({{pipe}})
```

### 图像滑动切换

图像滑动切换允许在保持相同提示词的情况下重新生成图像。如果设置了固定种子，下次生成时将随机化。通过 `/sd` 斜杠命令覆盖的图像尺寸在滑动切换图像时会保留。

要循环浏览图像，将鼠标光标悬停（移动端点击）在生成的图像上，即可显示箭头按钮和滑动计数器。点击最新图像上的右箭头将生成新图像。

*此处的"滑动切换"只是一个名称，不要尝试实际的滑动手势，因为那会重新生成消息本身，而不是附加的图像。*

## 选项

### 在生成前编辑提示词

此选项允许你在将自动生成的提示词发送到图像生成 API 之前进行编辑。你还可以在重新生成最初通过 `/sd` 命令创建的图像时，编辑或丢弃已保存的负面提示词并覆盖分辨率。

### 使用函数工具

使用[函数调用](/extensions/stable-diffusion/)自动检测生成图像的意图。

**要求：**

1. 必须配置了受支持的图像生成来源。
2. 必须使用受支持的聊天补全 API 模型，并在 AI 响应设置中启用了函数工具调用。
3. 必须在图像生成设置中启用"使用函数工具"选项。
4. 用户应在聊天消息中表达生成图像的意图，例如"给我发一张猫的图片"。

> **⚠️ Warning**
>
> 启用函数工具时，交互模式将不会触发。


### 使用交互模式

允许你触发图像生成而非文本，作为对符合以下特殊模式的用户消息的回复：

1. 包含以下动词之一：send、mail、imagine、generate、make、create、draw、paint、render
2. 后跟以下名词之一（距离不超过 10 个字符）：pic、picture、image、drawing、painting、photo、photograph
3. 后跟图像生成的目标主体，可选地前面带有"of a"或"of this"等短语。

有效请求及捕获主体的示例：

* `Can you please send me a picture of a cat` => `cat`
* `Generate a picture of the Eiffel tower` => `Eiffel tower`
* `Let's draw a painting of Mona Lisa` => `Mona Lisa`

某些特殊主体会触发预定义的生成模式：

* 'you'、'yourself' => "Yourself"
* 'your face'、'your portrait'、'your selfie' => "Your Face"
* 'me'、'myself' => "Me"
* 'story'、'scenario'、'whole story' => "The Whole Story"
* 'last message' => "The Last Message"
* 'background'、'scene background'、'scene'、'scenery'、'surroundings'、'environment' => "Background"

### 扩展自由模式提示词

使用斜杠命令的交互模式时，通过提示你的主 API 自动扩展自由模式生成的主体描述。

### 最小化提示词处理

启用后，减少对 LLM 返回的图像生成提示词的处理。仅执行规范化和空白缩减，跳过默认执行的激进清理。这在使用接受结构化提示词格式（如 JSON）的高级工作流（例如 ComfyUI）时非常有用。

### 对齐自动调整的分辨率

将强制宽高比（肖像、背景）的图像生成请求对齐到最近的已知分辨率，同时尽量保持绝对像素数。请参阅"分辨率"下拉菜单以获取可能的选项列表。

**推荐用于 SDXL 模型**。

## 通用提示词前缀

> **💡 专业提示**
>
> 使用 `{prompt}` 宏来精确指定生成的提示词将插入的位置。


添加在每个生成的或自由模式提示词之前。通常用于设置图片的整体风格。

示例：`best quality, anime lineart`。

## 负面提示词

你不希望出现在输出图像中的特征。

示例：`bad quality, watermark`。

## 角色专属提示词前缀

> **💡 专业提示**
>
> 如果生成来源支持，你还可以在此处使用 LoRA/嵌入，例如：`<lora:DonaldDuck:1>`。


描述当前所选角色的任何特征。将添加在通用前缀之后。

示例：`female, green eyes, brown hair, pink shirt`。

你还可以为任何不需要的内容指定负面提示词前缀。它将与通用负面提示词合并。

限制：
1. 仅在 1 对 1 聊天中有效。不会在群组中使用。
2. 不会用于背景和自由模式生成。

> **📝 Note**
>
> 要强制将角色前缀包含在自由模式提示词中，请在提示词中的任何位置使用 `{{charPrefix}}` 宏。


如果你想与他人分享前缀，请勾选"可分享"复选框。这将把它们与角色数据一起保存，而不是保存在你的本地设置中。

## 风格

使用此功能快速保存和恢复你喜欢的风格/质量预设，以便日后使用或在切换模型时使用。风格预设包含以下内容：

1. 通用提示词前缀
2. 负面提示词

你还可以使用 `/imagine-style` 命令（或 `/sd-style` 或 `/img-style`）在风格之间切换。

## 聊天消息可见性

插入到聊天中的生成图像默认在主 API 提示词中隐藏，但可以按生成发起者（"魔法棒"图标、斜杠命令、交互模式）单独覆盖。这可以用于通过让角色"感知"图像来使体验更加沉浸。如果启用了"发送内联图像"，聊天补全 API 中的多模态模型也可以"看到"图像。

可以通过更改图像提示词模板下的"聊天消息模板"来自定义文本消息。该模板中可以使用所有常规宏，外加一个特殊的 `{{prompt}}` 宏来指定图像提示词的添加位置。

## ComfyUI 配置

[ComfyUI](https://github.com/comfyanonymous/ComfyUI) 是一种快速且非常灵活的图像生成选项。

如果你熟悉 ComfyUI，简而言之：在 ComfyUI 中制作你的工作流，**以 API 格式**下载它，然后粘贴到 SillyTavern ComfyUI 工作流编辑器中。ST 会将你的工作流提交到 ComfyUI 的 API，你将在聊天中获得一张图像。但能力越大责任越大，主要责任是在工作流 JSON 中插入占位符，以便你可以从 SillyTavern 更改设置。

如果你不熟悉 ComfyUI，你仍然可以使用默认工作流在 SillyTavern 中生成图像。之后，当你想要更强大的功能时，你可以学习如何使用 ComfyUI……

### 控件

此面板允许你配置和管理与 SillyTavern 的 ComfyUI 集成。

#### 服务器类型

* 标准服务器是指你直接调用 ComfyUI，无论是在本地机器上还是托管在其他地方。
* RunPod 无服务器端点是通过 [RunPod 的无服务器 API](https://www.runpod.io/product/serverless) 运行 ComfyUI。无服务器对于远程生成来说是一个不错的选择，因为你可以获得与标准服务器相同的工作流控制，同时可以利用更强大的托管 GPU，并且只在主动生成图像时收费。大部分用法是相同的。与标准服务器设置和行为的差异在[下文](#comfyui-runpod-setup)中描述。

#### 标准服务器设置

在 **ComfyUI URL** 输入字段中输入你的 ComfyUI 服务器的 URL。默认值为 `http://127.0.0.1:8188`。
如果你使用的是 [SwarmUI](https://github.com/mcmonkeyprojects/SwarmUI)，
[托管的 ComfyUI 服务器](https://github.com/mcmonkeyprojects/SwarmUI/blob/master/src/BuiltinExtensions/ComfyUIBackend/README.md)的默认端口是 `7821`，
比 SwarmUI 的默认端口高 20 个端口。

输入 URL 后，选择 <i class="fa-solid fa-check"></i> **连接**以验证并建立连接。ComfyUI 服务器必须可以从 SillyTavern 主机机器访问。
 
#### ComfyUI RunPod 设置

* 你需要一个 RunPod 账户并向其中充值。在 RTX 4090 上使用 Qwen 图像生成，每张图像大约需要 2 美分，但具体情况因人而异。5 美元的额度应该能用一段时间。
* <https://console.runpod.io/hub/runpod-workers/worker-comfyui> 是一个 flux1 dev 配置，你可以用它来创建自己的无服务器端点。
  * 如果你想使用不同的模型或添加 LoRA，那里有关于创建自己配置的信息。
* 创建一个 API 密钥以访问无服务器端点：<https://console.runpod.io/user/settings>

* 在 ST 中，选择 **ComfyUI** 作为**来源**，选择 **RunPod 无服务器端点**作为**服务器类型**。
* 将 **ComfyUI RunPod URL** 设置为你的端点 URL。
* 设置 API 密钥。
* 点击**连接**。如果 API 密钥和 URL 正确，你应该会收到表示成功的提示。
* ComfyUI 工作流配置流程与本地相同。
  * 使用"导出（API）"选项。
  * 根据你的本地设置，你可能需要/想要选择模型的变体以在 RunPod 上使用。例如，如果你在本地使用量化的 GGUF，但想在 RunPod 上使用 fp16 版本。你在 ST 中使用的 JSON 工作流需要做此更改。
  * 模型、采样器、VAE 等无法动态确定，因此你的工作流需要硬编码这些（不支持 `%model%` 替换）。
  * 其他替换应与本地相同。

> **ℹ️ 注意**
>
> 无服务器配置目前不会将工作流嵌入到输出图像中。也就是说，你无法将图像拖放到本地 ComfyUI 中查看种子或提示词。这只是 RunPod 处理程序的限制，是可以在那一侧添加的功能。


### 工作流管理

从下拉菜单中选择一个 ComfyUI 工作流。提供了两个默认工作流：

- Default_Comfy_Workflow.json：一个基本的文本到图像工作流，支持最常见的图像生成设置。
- Char_Avatar_Comfy_Workflow.json：一个示例图像到图像工作流，使用角色头像加上提示词来生成图像。

使用以下按钮管理工作流：

- <i class="fa-solid fa-pen-to-square"></i> **打开工作流编辑器**以查看和修改所选工作流。
- <i class="fa-solid fa-plus"></i> **创建新工作流**以创建具有自定义名称的新工作流。
- <i class="fa-solid fa-trash-can"></i> **删除工作流**以移除所选工作流。

### 工作流编辑器

ComfyUI 工作流编辑器允许你查看和修改用于 SillyTavern 的 ComfyUI 工作流。

编辑器的主要组件是一个大型文本区域，你可以在其中以 JSON 格式插入或编辑你的 ComfyUI 工作流。

要将 ComfyUI 工作流添加到编辑器，请按照以下步骤操作：

1. 在 ComfyUI 设置中启用"开发者模式"。
2. 使用 ComfyUI 中的"保存（API 格式）"选项下载 JSON 数据。
3. 在 SillyTavern 中创建新工作流并打开编辑器。
4. 将下载的 JSON 数据粘贴到文本区域中。
5. 根据需要将特定值替换为占位符。

> **💡 提示**
>
> 你可以将 API 格式的 JSON 文件直接添加到 SillyTavern 安装目录中的 `data/default-user/user/workflows` 目录。这样可以省去步骤 3 和 4。
>
> 保留原始 JSON 文件。如果你需要再次在 ComfyUI 中打开工作流进行更改，编辑原始文件比编辑带有所有占位符的文件要方便得多。


### 占位符

编辑器提供了一组预定义占位符，可在你的工作流 JSON 中使用。当工作流在 SillyTavern 中执行时，这些占位符会被替换为动态值。

标记为 ✅ 的占位符存在于你的工作流 JSON 中。标记为 ❌ 的占位符不存在于你的工作流 JSON 中。你可以根据需要将这些占位符添加到工作流 JSON 中。你不需要添加所有占位符，只需添加你的工作流使用且你希望动态替换的那些。

#### 提示词

`%prompt%` 和 `%negative_prompt%` 占位符用于将图像生成提示词插入到工作流中。这些包含 SillyTavern 生成的最终提示词，包括为你选择的 `/sd` 模式生成的提示词、通用提示词前缀、负面提示词和角色专属提示词前缀。

例如，你可能在 ComfyUI 中用"forest elf"这样的提示词测试过你的工作流。要在 SillyTavern 中使用此工作流，你可以将"forest elf"提示词替换为 `%prompt%` 占位符：

+++ 带占位符的 JSON
```json
{
    "class_type": "CLIPTextEncode",
    "inputs": {
        "clip": ["4", 1],
        "text": "%prompt%"
    }
}
```
+++ 原始 JSON
```json
{
    "class_type": "CLIPTextEncode",
    "inputs": {
        "clip": ["4", 1],
        "text": "forest elf"
    }
}
```
+++

注意占位符被双引号包裹。这对 JSON 格式很重要，也是 SillyTavern 占位符替换系统所要求的。即使是数字，你也必须在模板 JSON 中使用双引号。

有时提示词（或其他值）不会出现在你预期的位置。如果不必要，ComfyUI 会从 API 版本的工作流中移除节点。

例如，此工作流使用了一个 [LoRA 标签加载器节点](https://github.com/badjeff/comfyui_lora_tag_loader)和提示词原语，以便在 UI 模式下工作流更清晰：

![提示词原语和 LoRA 加载器](/static/extensions/sd-comfy-prompt-primitive.png)

提示词原语节点将从 API 版本的工作流中移除，因此你在 LoraTagLoader 节点中插入占位符。在工作流中找到文本"apple tree"并将其替换为 `%prompt%` 占位符：

+++ 带占位符的 JSON
```json
{
    "inputs": {
      "text": "%prompt%",
      "model": ["112", 0],
      "clip": ["112", 1]
    },
    "class_type": "LoraTagLoader",
    "_meta": {"title": "Load LoRA Tag"}
}
```
+++ 原始 JSON
```json
{
    "inputs": {
      "text": "apple tree",
      "model": ["112", 0],
      "clip": ["112", 1]
    },
    "class_type": "LoraTagLoader",
    "_meta": {"title": "Load LoRA Tag"}
}
``` 
+++

在某些情况下，你可能需要在工作流 JSON 中进行多处替换，即使提示词在 UI 中只出现一次。

#### 模型

`%model%` 占位符将插入图像生成设置中所选模型的值。

来自默认文本到图像工作流的示例：

+++ 带占位符的 JSON
```json
{
    "class_type": "CheckpointLoaderSimple",
    "inputs": {
        "ckpt_name": "%model%"
    }
}
```
+++ 原始 JSON
```json
{
    "class_type": "CheckpointLoaderSimple",
    "inputs": {
        "ckpt_name": "sd15.safetensors"
    }
}
```
+++

要加载 GGUF 量化的 UNet，请在工作流中使用 [UNet 加载器（GGUF）](https://github.com/city96/ComfyUI-GGUF)节点，
在 SillyTavern 模型下拉菜单中选择 `GGUF` 模型，并在节点设置中使用 `%model%` 占位符，如下所示：

+++ 带占位符的 JSON
```json
{
    "inputs": {
      "unet_name": "%model%"
    },
    "class_type": "UnetLoaderGGUF",
    "_meta": {
      "title": "Unet Loader (GGUF)"
    }
}
```
+++ 原始 JSON
```json
{
    "inputs": {
      "unet_name": "flux1-dev-Q4_0.gguf"
    },
    "class_type": "UnetLoaderGGUF",
    "_meta": {
      "title": "Unet Loader (GGUF)"
    }
}
```
+++

> **ℹ️ 如果你的 ComfyUI 中有除常规 SD 检查点之外的模型类型**
>
> Stable Diffusion 检查点、SD UNet 和 GGUF 量化的 UNet 都会出现在模型下拉菜单中。
> 一种类型的模型无法与期望另一种类型的 workflows/loader 节点一起使用。
> 如果你在 ST 中选择了不兼容的模型类型，ComfyUI 将报告加载器节点的问题。


#### 头像图像

使用 `%user_avatar%` 和 `%char_avatar%` 占位符将用户和角色头像包含在工作流中。当工作流执行时，这些占位符会被替换为头像的 PNG 数据。图像数据以 base64 格式编码，因此你必须在工作流中解码它。一个常用的选择是 [Load image (Base64)](https://github.com/Acly/comfyui-tooling-nodes) 节点。

在此示例中，角色头像通过 `Load Image (Base64)` 节点加载。它还使用 Image Resize 节点将图像缩放到图像生成设置中指定的尺寸：

![从 base64 字符串加载图像并调整大小](/static/extensions/sd-comfy-load-b64.png)

将 `%char_avatar%`、`%width%` 和 `%height%` 占位符插入到 Load Image (Base64) 和 Image Resize 节点的 JSON 中：

```json
{
    "97": {
        "inputs": {
            "image": "%char_avatar%"
        },
        "class_type": "ETN_LoadImageBase64",
        "_meta": {"title": "Load Image (Base64)"}
    },
    "98": {
        "inputs": {
            "mode": "resize",
            "resize_width": "%width%",
            "resize_height": "%height%",
            "image": ["97", 0]
        },
        "class_type": "Image Resize",
        "_meta": {"title": "Resize image"}
    }
}
```

要获取用于在 ComfyUI 中测试工作流的 base64 编码图像字符串，请使用任何将图像转换为 base64 字符串的在线工具。
以下是一个可用于初始测试的示例字符串：[sd-comfy-base64-test-string.txt](/static/extensions/sd-comfy-base64-test-string.txt)。

#### 其他占位符

大多数其他占位符使用图像生成设置中相应控件的值，或你通过 `/sd` 命令指定的值：

- `%vae%`，但大多数 SD 模型包含 VAE，因此默认工作流不使用此占位符。将其与自定义工作流一起使用，以在加载 UNet 的同时加载 VAE、覆盖默认 VAE 等。
- `%sampler%`
- `%scheduler%`
- `%steps%`
- `%scale%`
- `%width%`
- `%height%`
- `%denoise%`：对于示例图像到图像工作流，在约 0.5（对源图像几乎不可察觉的变化）和 1.0（完全不同的图像，就像没有使用源图像一样）之间调整降噪量。默认文本到图像工作流不使用此参数，因为对于文本到图像来说，使用 1.0 以外的值没有意义。
- `%clip_skip%`：默认工作流不使用，但可用于自定义工作流。

如果你指定了种子值，`%seed%` 占位符将插入控件中的种子值。如果你将种子设置为 `-1`，SillyTavern 将为 `%seed%` 中的每张图像生成一个新的随机种子。

#### 自定义占位符

你可以向工作流添加自定义占位符：

1. 查找预定义占位符下方的"自定义"部分。
2. 点击"+"按钮添加新的自定义占位符。
3. 在 `find` 字段中输入占位符的名称。
4. 在 `replace` 字段中输入要替换占位符的值。

自定义占位符将出现在预定义占位符下方的单独列表中。

例如，你可以将默认工作流中保存图像文件名的"SillyTavern"前缀替换为自定义占位符。添加一个新的自定义占位符，将 `find` 设置为 `filename_prefix`，将 `replace` 设置为 `ServiceTensor`。将新的 `%filename_prefix%` 占位符插入到你的工作流 JSON 中。现在你可以通过更改自定义占位符的值，将文件名前缀从 SillyTavern 更改为 ServiceTensor。

+++ 带占位符的 JSON
```json
{
    "class_type": "SaveImage",
    "inputs": {
        "filename_prefix": "%filename_prefix%",
        "images": ["8", 0]
    }
}
```
+++ 原始 JSON
```json
{
    "class_type": "SaveImage",
    "inputs": {
        "filename_prefix": "SillyTavern",
        "images": ["8", 0]
    }
}
```
+++

### Comfy 技巧

阅读本页上的所有通用信息，以便熟悉图像生成选项。诸如可切换风格和通用提示词前缀等选项，结合 ComfyUI 工作流的完全灵活性，允许你创建各种各样的图像生成设置。

#### 加载 LoRA

使用 LoRA 标签加载器节点（如 [Load LoRA Tag](https://github.com/badjeff/comfyui_lora_tag_loader)）来加载提示词中指定的任何 LoRA。
现在你可以使用 `<lora:CroissantStyle:0.8>` 等标签在提示词中添加任意数量的 LoRA，它们将被加载到你的工作流中。
这也将使在[角色专属提示词前缀](#character-specific-prompt-prefix)中使用 LoRA 的"专业提示"与 ComfyUI 兼容。

#### 从风格或斜杠命令设置工作流值

你可以在自定义占位符值中使用宏。举一个实际的例子，
假设你有时想生成没有背景的图像，并且希望通过斜杠命令或图像风格来切换。以下是实现方法：

1. 制作一个 ComfyUI 工作流，根据输入值决定是否移除图像背景
2. 使用自定义占位符设置该输入的值，但使用 `{{getvar::remove_background}}` 作为替换值
3. 现在你可以在生成图像前使用 `/setvar key=remove_background true` 或 `/setvar key=remove_background false` 设置 `remove_background` 的值
4. 工作流将使用你设置的值来决定是否移除背景
5. 创建一个图像风格"No background"，通用提示词前缀为 `{{setvar::remove_background::true}}`
6. 使用风格控件或 `/imagine-style No background` 在生成图像前将 `remove_background` 的值设置为 `true`