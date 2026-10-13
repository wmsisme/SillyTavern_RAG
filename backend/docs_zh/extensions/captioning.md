
# 图像描述

图像描述功能允许 SillyTavern 为聊天中使用的图像自动生成文字描述。

当你希望 AI 角色能够“看到”并回应对话中的视觉内容时，可以使用图像描述功能。

- 为你上传或粘贴到消息中的图像创建描述
- 为聊天历史中已有的图像添加上下文
- 使用多种生成来源，包括本地模型、云端 API 和众包网络

有些选项无需任何设置、无需付费、也不需要 GPU。也有一些选项需要其中一项或全部条件。请根据你的需求和资源选择适合的方案。

图像描述扩展内置于 SillyTavern 中，无需单独安装。

## 快速开始

1. 设置：
    - 在 **<i class="fa-solid fa-cubes"></i> 扩展** 面板中打开 **图像描述** 面板
    - 选择一个描述来源（通常是“本地”或“多模态”）
    - 如果选择“多模态”，请确保已在 **<i class="fa-solid fa-plug"></i> API 连接** 标签页中设置好连接
2. 生成描述：
    - 从 **<i class="fa-solid fa-magic-wand-sparkles"></i> 扩展** 弹出菜单中选择“**生成描述**”
    - 在提示时选择图像文件
    - 等待描述生成
3. 查看并发送：
    - 带有描述的图像将被插入到你的消息中
    - 通过图像工具提示查看描述
    - 点击 **<i class="fa-solid fa-paper-plane"></i> 发送**，看看你的角色对这张图像有什么看法！

## 面板控件

### 来源选择

选择图像描述的来源。支持的选项：

| 来源                           | 描述                                                                                                                                                                                                  |
|----------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [多模态](#多模态来源) | **云端**：OpenAI、Anthropic、Google、MistralAI 等。<br>**本地**：Ollama、llama.cpp、KoboldCpp、Text Generation WebUI 和 vLLM。<br>支持自定义提示词，因此你可以向图像提问。 |
| [本地](#本地来源)           | 使用在你的 SillyTavern 服务器本地运行的 [transformers.js](https://huggingface.co/docs/transformers.js/en/index)。零配置！                                                                     |
| Horde                            | 使用 [AI Horde](https://aihorde.net/) 网络，这是一个众包分布式图像生成模型网络。无需下载、配置或付费。响应时间不固定。                       |
| Extras                           | Extras 项目已于 2024 年 4 月停止，不再维护或支持。                                                                                                                        |

### 描述配置
- **描述提示词**：输入用于描述的自定义提示词。默认提示词为“What's in this image?”
- **每次询问**：开启后，每次生成图像描述时都会请求自定义提示词

### 消息模板
- **消息模板**：自定义描述消息模板。使用 `{{caption}}` 宏来插入生成的描述。默认模板为 `[{{user}} sends {{char}} a picture that contains: {{caption}}]`

### 自动描述
- **自动为图像生成描述**：开启后，粘贴或附加到消息中的图像将自动生成描述
- **保存前编辑描述**：开启后，允许在保存描述之前进行编辑

## 为图像生成描述

在 SillyTavern 中为图像生成描述的所有方式：

* 从 **<i class="fa-solid fa-magic-wand-sparkles"></i> 扩展** 弹出菜单中选择“**生成描述**”，并在提示时选择图像文件
* 点击消息中已有图像顶部的 <i class="fa-solid fa-envelope-open-text"></i> **描述** 图标
* 在启用[自动描述](#自动描述)的情况下，直接将图像粘贴到聊天输入框中
* 使用消息操作中的 <i class="fa-solid fa-paperclip"></i> **嵌入文件或图像** 按钮将图像文件附加到消息中
* 发送带有嵌入图像的消息
* 使用 `/caption` [斜杠命令](#斜杠命令-caption)

## 自动描述
自动描述功能允许你在图像添加到聊天时自动生成描述，而无需每次手动触发描述过程。

要启用此功能，请在图像描述面板中勾选“自动为图像生成描述”复选框。你还可以通过勾选“保存前编辑描述”框来选择在保存描述之前进行编辑。

启用后，自动描述将在以下场景中触发：

- 当图像直接粘贴到聊天输入框中时。
- 当图像文件附加到消息中时。
- 当发送带有嵌入图像的消息时。

系统将使用你选择的描述来源（本地、Extras、Horde 或多模态）以及配置的设置来为图像生成描述。

### 保存前编辑描述（精炼模式）

如果你启用了“保存前编辑描述”选项：
1. 添加图像后，将弹出一个包含生成描述的窗口。
2. 你可以根据需要查看和编辑描述。
3. 点击“确定”应用描述，或点击“取消”放弃描述而不保存。

### 描述发送
生成（并可选择编辑）的描述将使用你配置的消息模板自动插入到提示词中。默认情况下，它将按以下格式发送：

```
[BaronVonUser sends Seraphina a picture that contains: ...]
```


## 斜杠命令：/caption
该扩展提供了一个 `/caption` 斜杠命令，可在聊天框或脚本中使用。

### 用法

```
/caption [quiet=true|false]? [mesId=number]? [prompt]
```

- `prompt`（可选）：用于描述模型的自定义提示词。仅多模态来源支持。
- `quiet=true|false`：如果设置为 true，则不会向聊天发送带有描述的消息。默认为 false。
- `mesId=number`：指定一个消息 ID，以便从已有消息中为图像生成描述，而不是上传新图像。

如果未提供 `mesId`，该命令将提示你上传图像。当 `quiet` 为 false（默认值）时，将向聊天发送一条带有描述图像的新消息。生成的描述可用作其他命令的输入。

### 示例
使用默认设置为新图像生成描述：

```
/caption
```

使用自定义提示词为新图像生成描述：

```
/caption Describe the main colours and shapes in this image
```

为第 5 条消息中的图像生成描述，但不发送新消息：

```
/caption mesId=5 quiet=true
```

为第 10 条消息中的图像使用自定义提示词生成描述，然后根据该描述[生成新图像](/extensions/stable-diffusion/)：

```
/caption mesId=10 Describe this image using comma-separated keywords | /imagine 
```

## 本地来源

你可以在 [config.yaml](/administration/config-yaml/#extensions-configuration) 中更改模型。对应的键名为 `extensions.models.captioning`。输入你想使用的 Hugging Face 模型 ID。默认值为 `Xenova/vit-gpt2-image-captioning`。

你可以使用任何支持图像描述的模型（`VisionEncoderDecoderModel` 或“image-to-text”管道）。该模型需要与 transformers.js 库兼容。也就是说，它需要 ONNX 权重。请寻找带有 `ONNX` 和 `image-to-text` 标签的模型，或者包含一个装满 `.onnx` 文件的 `onnx` 文件夹的模型。

## 多模态来源

### 通用配置

- **模型**：选择用于图像描述的模型。选项因所选 API 而异。
- **允许反向代理**：开启后，如果已定义且有效，则允许使用反向代理（OpenAI、Anthropic、Google、Mistral、xAI）

描述来源的 API 密钥和端点 URL 在 [API 连接](/usage/api-connections/) 面板中管理。请先在 API 连接中设置好连接，然后在图像描述中选择它作为描述来源。

> **⚠️ 请先在 API 连接面板中进行设置**
>
> 再说一次：在 **<i class="fa-solid fa-plug"></i> API 连接** 中配置 API 密钥/地址/端口，并在图像描述中使用该连接。
>
> 你仍然可以使用 Claude 进行聊天，使用 Google AI Studio 进行图像描述，或者随便什么组合。只需先在“API 连接”标签页中将它们*都*设置好。然后将你的聊天补全来源切换为 Claude，将图像描述来源切换为 Google AI Studio。


对于大多数本地后端，你需要在模型后端而不是在 SillyTavern 中设置一些选项。如果你的后端一次只能运行一个模型且不支持自动切换，你有几种选择来为聊天和图像描述使用不同的模型：

1. **辅助端点：** 使用辅助端点功能（参见下方[辅助端点](#辅助端点)部分）连接到不同的 API 服务器进行图像描述
2. **多种连接类型：** 在 API 连接中同时使用文本补全和聊天补全模式连接到你的后端——这样你就有了到同一后端类型的两个独立连接

### 来源

要使用以下描述来源之一，请在来源下拉菜单中选择“多模态”。

* “我想要尽可能最好的描述，而且不介意付费”：Anthropic
* “我不想付任何费用，也不想运行任何东西”：Google AI Studio 免费套餐
* “我想在本地生成图像描述，而且希望它能直接工作”：Ollama
* “我想让本地 AI 的梦想继续下去”：[KoboldCpp](#koboldcpp)
* “我想在它不工作时抱怨”：~~Extras~~

| API 提供商                      | 描述                                                                                                                                                                   |
|-----------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| AI/ML API                         | 云端，付费，各种具有视觉能力的 GPT、Claude 和 Gemini 模型                                                                                                  |
| Chutes                            | 云端，各种具有视觉能力的模型                                                                                                                                |
| Claude                            | 云端，付费，所有具有视觉能力的 Claude 模型                                                                                                                       |
| Cloudflare Workers AI             | 云端，付费，各种具有视觉能力的模型                                                                                                                          |
| Cohere                            | 云端，付费，Aya Vision 8B / 32B                                                                                                                                              |
| 自定义（OpenAI 兼容）        | 用于自定义 OpenAI 兼容 API，使用 API 连接标签页中当前配置的模型                                                                                     |
| Electron Hub                      | 云端，付费，各种具有视觉能力的模型。                                                                                                                         |
| Google AI Studio                  | 云端，免费套餐后付费，Gemini Flash/Pro                                                                                                                                  |
| Google Vertex AI                  | 云端，免费套餐，Gemini Flash/Pro                                                                                                                                            |
| Groq                              | 云端，llama-4 scout/maverick                                                                                                                                                 |
| KoboldCpp                         | 本地，必须在 KoboldCpp 中配置模型                                                                                                                                      |
| llama.cpp                         | 本地，必须在 llama.cpp 中配置模型                                                                                                                                      |
| MistralAI                         | 云端，付费，pixtral-large、pixtral-12B、magistral、mistral-large 等                                                                                                       |
| Moonshot AI                       | 云端，付费，moonshot-vision                                                                                                                                                  |
| NanoGPT                           | 云端，付费，各种具有视觉能力的 GPT/Claude/Google 模型                                                                                                        |
| Ollama                            | 本地，在 API 连接中配置后，可在图像描述中切换可用模型并下载[额外的视觉模型](https://ollama.com/search?c=vision) |
| OpenAI                            | 云端，付费，GPT-4 Vision、4-turbo、4o、4o-mini                                                                                                                               |
| OpenRouter                        | 云端，付费（可能有免费选项），大量模型，在 API 连接中配置后可在图像描述中从可用模型中选择                                              |
| Pollinations                      | 云端，免费                                                                                                                                                                   |
| Text Generation WebUI (oobabooga) | 本地，必须在 ooba 中配置模型                                                                                                                                           |
| vLLM                              | 本地                                                                                                                                                                         |
| xAI (Grok)                        | 云端，付费，grok-vision                                                                                                                                                      |
| Z.AI (GLM).                       | 云端，付费，GLM Vision 模型                                                                                                                                                |

### 辅助端点

默认情况下，多模态来源使用 API 连接标签页中配置的主端点。
你也可以专门为多模态图像描述设置一个辅助端点。

- 在 **<i class="fa-solid fa-cubes"></i> 扩展** 面板中打开 **图像描述** 面板。
- 选择“多模态”作为描述来源，并选择一个首选的 API 提供商。
- 在“辅助描述端点 URL”字段中输入辅助端点的有效 URL。
- 勾选“使用辅助 URL”框以启用辅助端点。

> **💡 Tip**
>
> 不要在 URL 末尾附加 `/v1` 或 `/chat/completions`。扩展会自动处理。


仅以下 API 支持此功能：

- KoboldCpp
- llama.cpp
- Ollama
- Text Generation WebUI (oobabooga)
- vLLM

### 来源特定指南

#### KoboldCpp

有关安装和使用 [KoboldCpp](https://github.com/LostRuins/koboldcpp) 的一般信息，请参阅 [KoboldCpp 文档](https://github.com/LostRuins/koboldcpp/wiki)。

要使用 KoboldCpp 进行多模态图像描述：

* 获取一个支持多模态的模型，该模型经过训练可以同时处理文本和图像提示。
* 同时获取该模型的多模态投影文件。这些权重允许模型理解输入中文本和图像部分之间的关系。
* 在 KoboldCpp 启动 GUI 或命令行界面中加载模型和投影文件。

最初且经典的本机多模态模型是 LLaVA。该模型和投影文件的 GGUF 格式文件可从 [Mozilla/llava-v1.5-7b-llamafile](https://huggingface.co/Mozilla/llava-v1.5-7b-llamafile) 获取。要从命令行加载它们，请使用 `--model` 和 `--mmproj` 标志设置模型和投影文件。例如：

```shell
./koboldcpp \
--model="models/llava-v1.5-7b-Q4_K.gguf" \
--mmproj="models/ llava-v1.5-7b-mmproj-Q4_0.gguf" \
... other flags ...
```

你可以尝试的一些 LLaVA 微调模型：[xtuner/llava-llama-3-8b-v1_1-gguf](https://huggingface.co/xtuner/llava-llama-3-8b-v1_1-gguf)、[xtuner/llava-phi-3-mini-gguf](https://huggingface.co/xtuner/llava-phi-3-mini-gguf)。

你可以使用你的特定微调模型所基于的基础模型的多模态投影文件。一些常见基础模型的投影文件可从 [koboldcpp/mmproj](https://huggingface.co/koboldcpp/mmproj/tree/main) 获取。