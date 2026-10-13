
# 推理

在语言模型中，推理（也称为模型思考）指的是一种思维链（CoT）技术，通过逐步分析来模拟人类解决问题的方式。SillyTavern 提供了若干功能，使推理模型在受支持的后端上的使用更加高效和一致。

## 常见问题

1. 使用推理模型时，模型的内部推理过程会消耗一部分响应令牌配额，即使这些推理内容不会显示在最终输出中（例如 o3-mini 或 Gemini Thinking）。如果你发现响应返回不完整或为空，应尝试调整 **<i class="fa-solid fa-sliders"></i> AI Response Configuration** 面板中的 Max Response Length 设置。对于推理模型，通常会使用比标准对话模型高得多的令牌限制——大约在 1024 到 4096 个令牌之间。

## 配置

> **📝 提示**
大多数与推理相关的设置可以在 **<i class="fa-solid fa-font"></i> Advanced Formatting** 面板的“Reasoning”部分进行配置。
> **📝 提示**

推理块在聊天中以可折叠消息段的形式显示。它们可以手动添加、由后端自动添加，或通过响应解析添加（见下文）。

默认情况下，推理块处于折叠状态以节省空间。点击某个块可展开并查看其内容。你可以在推理设置中启用 **Auto-Expand** 来让推理块自动展开。

当推理块展开时，你可以使用 **<i class="fa-solid fa-copy"></i> Copy** 和 **<i class="fa-solid fa-pencil"></i> Edit** 按钮复制或编辑其内容。

某些模型支持推理，但不会将思考内容返回。对于这些模型，可以通过切换 **Show Hidden** 设置来显示带有推理时间的推理块。

## 添加推理

### 手动添加

通过 **<i class="fa-solid fa-pencil"></i> Message Edit** 菜单为任意消息添加推理块。在编辑时点击 **<i class="fa-solid fa-lightbulb"></i>** 即可添加推理部分。第三方扩展也可以在将消息对象添加到聊天之前，通过写入消息对象的 `extra.reasoning` 字段来添加推理。

### 使用命令

使用 `/reasoning-set` STscript 命令为消息添加推理。该命令接受 `at`（消息 ID，默认为最后一条消息）和推理文本作为参数。

```stscript
/reasoning-set at=0 This is the reasoning for the first message.
```

### 通过后端添加

如果你选择的 LLM 后端和模型支持推理输出，在 **<i class="fa-solid fa-sliders"></i> AI Response Configuration** 面板中启用“Request model reasoning”将添加一个包含模型思考过程的推理块。

支持的来源：

- Claude
- DeepSeek
- Google AI Studio
- Google Vertex AI
- OpenRouter
- xAI (Grok)
- AI/ML API
- Z.AI
- Pollinations
- MistralAI
- Electron Hub
- Chutes
- NanoGPT
- Moonshot

> **📝 提示**
对于**大多数**来源，“Request model reasoning”并不决定模型是否进行推理，因为推理无法被禁用。如果后端和模型支持显式请求禁用推理，该设置将这样做。否则，模型将始终进行推理。
> **📝 提示**

各提供商特定说明：

- Claude 和 Google（2.5 Flash）允许切换思考模式；请参阅[推理强度](#reasoning-effort)。
- 可以为 [Z.AI (GLM)](https://docs.z.ai/api-reference/llm/chat-completion#body-one-of-0-thinking) 和 [Moonshot (Kimi)](https://platform.moonshot.ai/docs/guide/use-kimi-k2-thinking-model) 禁用推理。该设置映射到 `thinking.type` 参数。它们不支持“Reasoning Effort”。
- 对于 OpenRouter，当“Request model reasoning”开关被停用且设置了最小推理强度时，对于支持该功能的模型，思考将被设置为禁用。具体行为取决于模型；某些提供商可能会拒绝此类请求。

### 通过解析添加

在 **<i class="fa-solid fa-font"></i> Advanced Formatting** 面板中启用“Auto-Parse”，以自动从模型输出中解析推理内容。

响应必须包含一个用配置的前缀和后缀序列包裹的推理部分。默认提供的序列对应 DeepSeek R1 推理格式。对于某些返回未解析推理内容的 API 来源（如 MiniMax 或 Perplexity），必须启用此功能。

使用前缀 `<think>` 和后缀 `</think>` 的示例：

```txt
<think>
This is the reasoning.
</think>

This is the main content.
```

## 使用推理进行提示

默认情况下，识别出的推理块内容不会被发送回模型。要将推理内容包含在提示中，请在 **<i class="fa-solid fa-font"></i> Advanced Formatting** 面板中启用“Add to Prompts”。推理内容将被包裹在配置的前缀和后缀序列中，并通过分隔符与主上下文分开。Max Additions 数值设置控制可以包含多少个推理块，从提示末尾开始计数。

> **📝 提示**
大多数模型提供商不建议在多轮对话中将思维链发送回模型。
> **📝 提示**

### 从推理继续

一种特殊情况是，当生成被继续时（例如通过 **<i class="fa-solid fa-bars"></i> Options** 菜单按下“Continue”），可以在未启用“Add to Prompts”开关的情况下将推理发送回模型，但被继续的消息仅包含推理而没有实际内容。这给了模型一个机会来完成不完整的推理并开始生成主要内容。提示将按如下方式发送：

```txt
<think>
Incomplete reasoning...
```

## 正则表达式脚本

来自 [Regex 扩展](/extensions/regex/)的正则表达式脚本可以应用于推理块的内容。在脚本编辑器的“Affects”部分勾选“Reasoning”以专门针对推理块。

不同的临时性选项对推理块的影响如下：

1. 无临时性：推理内容被永久更改。
2. 编辑时运行：当推理块被编辑时，正则表达式脚本将被重新评估。
3. 更改聊天显示：正则表达式应用于推理块的显示文本，而非底层内容。
4. 更改发送的提示：正则表达式仅在推理块发送到模型之前应用于推理块。

## 推理强度

Reasoning Effort 是 **<i class="fa-solid fa-sliders"></i> AI Response Configuration** 面板中的一个 Chat Completion 设置，影响可能用于推理的令牌数量。每个选项的效果取决于所连接的来源。对于以下来源，Auto 仅表示请求中不包含相关参数。

| 选项    | Claude（无流式传输时 ≤ 21333）   | OpenAI（关键词）     | OpenRouter（关键词）             | xAI (Grok)（关键词） | Perplexity（关键词） | NanoGPT（关键词） |
| ------- | -------------------------------- | -------------------- | -------------------------------- | -------------------- | -------------------- | ----------------- |
| 模型    | Opus 4, Sonnet 4/3.7             | o4-mini, o3\*, o1\*  | 适用的模型                       | grok-3-mini          | sonar-deep-research  | 适用的模型        |
| Auto    | 未指定，**无思考**               | 未指定               | 未指定，效果取决于模型           | 未指定               | 未指定               | 未指定            |
| Minimum | 预算 1024 个令牌                 | "low"                | "low"，或最大响应的 20%          | "low"                | "low"                | "none"            |
| Low     | 最大响应的 15%，最低 1024        | "low"                | "low"，或最大响应的 20%          | "low"                | "low"                | "minimal"         |
| Medium  | 最大响应的 25%，最低 1024        | "medium"             | "medium"，或最大响应的 50%       | "low"                | "medium"             | "low"             |
| High    | 最大响应的 50%，最低 1024        | "high"               | "high"，或最大响应的 80%         | "high"               | "high"               | "medium"          |
| Maximum | 最大响应的 95%，最低 1024        | "high"               | "high"，或最大响应的 80%         | "high"               | "high"               | "high"            |

- 对于不支持自适应思考的旧版 Claude 模型，如果禁用流式传输，预算上限为 21333。如果计算出的预算低于 1024，则最大响应改为 2048。
- Claude 还支持 Opus 4.6+ 模型的自适应思考，可通过 [config.yaml](/administration/config-yaml/) 中的 `claude.enableAdaptiveThinking` 启用（Opus 4.7+ 始终启用）。启用后，Reasoning Effort 设置将映射到自适应思考级别而非令牌预算。对于适用的模型，此设置优先于“Verbosity”设置。
- 对于 OpenRouter、Pollinations、Perplexity、xAI、Chutes、DeepSeek、AI/ML API、xAI、Electron Hub，仅发送 OpenAI 风格的关键词。
- 对于 OpenAI 上的 GPT-5.4 和 GPT-5.5 模型，“Minimal”推理强度对应“none”，即禁用推理。
- 对于作为 Chat Completion Custom API 来源运行的 KoboldCpp，推理强度作为 `reasoning_effort` 参数发送，值为“minimal”、“low”、“medium”、“high”和“xhigh”。
- 对于其他 Custom（OpenAI 兼容）来源，仅当模型在官方 OpenAI 来源上支持时才会发送推理强度。

Google AI Studio 和 Vertex AI 如下：

| 模型           | Auto（动态思考）        | Minimum            | Low                          | Medium     | High       | Maximum               |
| -------------- | ----------------------- | ------------------ | ---------------------------- | ---------- | ---------- | --------------------- |
| 2.5 Pro        | thinkingBudget = -1     | 128                | 最大响应的 15%，最低 128     | 最大响应的 25% | 最大响应的 50% | 最大响应或 32768 中的较低值 |
| 2.5 Flash      | thinkingBudget = -1     | 0，**无思考**      | 最大响应的 15%               | 最大响应的 25% | 最大响应的 50% | 最大响应或 24576 中的较低值 |
| 2.5 Flash Lite | thinkingBudget = -1     | 0，**无思考**      | 最大响应的 15%，最低 512     | 最大响应的 25% | 最大响应的 50% | 最大响应或 24576 中的较低值 |
| 3.0/3.1 Pro    | thinkingLevel = null    | "low"              | "low"                        | "low"      | "high"     | "high"                |
| 3.0/3.1 Flash  | thinkingLevel = null    | "minimal"          | "low"                        | "medium"   | "high"     | "high"                |

- 对于 Gemini 2.5 Pro 和 2.5 Flash/Lite，无论流式传输设置如何，预算分别上限为 32768 或 24576 个令牌。