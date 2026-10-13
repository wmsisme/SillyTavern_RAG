
# 函数调用

函数调用允许通过让 LLM 使用结构化数据来为扩展添加动态功能，然后你可以使用这些数据来触发扩展的特定功能。

## 示例用例

1. 查询外部 API 以获取附加信息（新闻、天气、网络搜索等）。
2. 根据用户输入执行计算或转换。
3. 存储和回忆重要的记忆或事实，包括 RAG 和数据库查询。
4. 在对话中引入真正的随机性（掷骰子、抛硬币等）。

## 官方支持函数调用的扩展

1. [图像生成](/extensions/stable-diffusion/)（内置）- 根据用户提示生成图像。
2. [网络搜索](/extensions/websearch/) - 针对查询触发网络搜索。
3. [RSS](https://github.com/SillyTavern/Extension-RSS/) - 从 RSS 源获取最新新闻。
4. [天气](https://github.com/SillyTavern/Extension-Weather) - 从天气 API 获取天气信息。
5. [D&D 骰子](https://github.com/SillyTavern/Extension-Dice) - 为 D&D 游戏掷骰子。

## 前提条件和限制

1. 此功能仅适用于聊天补全 API，支持以下来源：Custom (OpenAI 兼容)、AI/ML API、AI21、Azure OpenAI、Chutes、Claude、Cloudflare Workers AI、Cohere、DeepSeek、Electron Hub、Fireworks、Google AI Studio、Google Vertex AI、Groq、MiniMax、MistralAI、Moonshot (Kimi)、NanoGPT、OpenAI、OpenRouter、Pollinations、SiliconFlow、xAI (Grok) 和 Z.AI (GLM)。
2. 文本补全 API 不支持函数调用，但一些本地托管的后端（如 Ollama 和 TabbyAPI）可以在聊天补全下以 Custom OpenAI 兼容模式运行。
3. 函数调用的支持必须首先由用户明确允许。这通过启用 AI 响应配置面板中的“启用函数调用”选项来完成。
4. 无法保证 LLM 会执行任何函数调用。大多数函数调用需要通过提示显式“激活”（例如，用户要求“掷骰子”、“获取天气”等）。
5. 并非所有提示都能触发工具调用。续写、扮演、后台（“静默”）提示不允许触发工具调用。它们仍然可以在响应中使用过去成功的工具调用。
6. 某些模型可能不支持函数调用，即使 API 来源支持。有关哪些模型支持函数调用的详细信息，请参阅你的 API 提供商的文档。

## 工具调用递归限制

为了防止工具调用的无限循环，存在一个递归限制（默认：5 轮）。如果 LLM 持续重复调用工具，执行将在达到限制后停止。你可以在 AI 响应配置设置中调整此限制，位于“启用函数调用”选项旁边。

## 交错思考

在使用工具调用与[推理模型](/usage/prompts/reasoning/)时，你可以利用随工具调用请求一起返回的推理来维持交错思考上下文。对于某些模型，这是确保工具调用之间一致性和保留重要细节所必需的。

在 AI 响应配置中选择以下设置之一：

- 禁用：工具调用请求中不包含推理上下文。兼容性最高，默认设置。
- 自上次用户消息以来：包含最新用户消息之后发生的任何工具轮次的推理。
- 活动工具链：仅仍在当前未解决的“工具循环”内时包含推理；一旦产生正常的助手回复，旧的“工具链”推理将不再重新发送。

## 如何制作函数工具

### 检查是否支持该功能

使用 `SillyTavern.getContext()` 中的 `isToolCallingSupported()` 来检查当前 API 是否支持函数工具调用以及是否在设置中启用：

```js
const { isToolCallingSupported } = SillyTavern.getContext();

if (isToolCallingSupported()) {
    console.log('Function tool calling is supported');
}
```

你还可以检查是否可以为特定生成类型执行工具调用。续写、扮演和后台（“静默”）提示不允许触发工具调用：

```js
const { canPerformToolCalls } = SillyTavern.getContext();

if (canPerformToolCalls('normal')) {
    console.log('Can perform tool calls for this generation');
}
```

### 注册函数工具

使用 `SillyTavern.getContext()` 中的 `registerFunctionTool()` 来注册工具。工具定义遵循 [JSON Schema](https://json-schema.org/) 格式的参数：

```js
const { registerFunctionTool } = SillyTavern.getContext();

registerFunctionTool({
    name: 'get_weather',
    displayName: 'Get Weather',
    description: 'Get the current weather for a given location',
    parameters: {
        $schema: 'http://json-schema.org/draft-04/schema#',
        type: 'object',
        properties: {
            location: {
                type: 'string',
                description: 'The city name, e.g. "London"',
            },
            unit: {
                type: 'string',
                enum: ['celsius', 'fahrenheit'],
                description: 'Temperature unit',
            },
        },
        required: ['location'],
    },
    action: async ({ location, unit }) => {
        // Perform your logic here (API calls, computations, etc.)
        const data = await fetchWeatherData(location, unit);
        return JSON.stringify(data);
    },
    formatMessage: ({ location }) => `Checking weather for ${location}...`,
    shouldRegister: () => isWeatherFeatureEnabled(),
    stealth: false,
});
```

### 注册字段

| 字段 | 必需 | 描述 |
|-------|----------|-------------|
| `name` | 是 | 工具的唯一标识符 |
| `displayName` | 否 | 在 UI 中显示的用户友好显示名称 |
| `description` | 是 | 发送给 LLM 的描述，用于解释工具的功能以及何时使用它 |
| `parameters` | 是 | 定义工具输入参数的 JSON Schema |
| `action` | 是 | 当 LLM 调用工具时调用的函数。接收解析后的参数作为对象。可以是异步的。必须返回字符串结果（非字符串值将被 JSON 字符串化）。 |
| `formatMessage` | 否 | 返回一个字符串的函数，在工具执行时作为提示显示。返回空字符串以抑制提示。 |
| `shouldRegister` | 否 | 返回布尔值的函数；如果为 `false`，则该工具从当前请求中排除。如果未提供，则该工具为每个提示注册。 |
| `stealth` | 否 | 如果为 `true`，工具调用结果不会记录到可见的聊天历史中，也不会触发后续生成 |

### 注销函数工具

要停用函数工具，请使用工具名称调用 `unregisterFunctionTool()`：

```js
const { unregisterFunctionTool } = SillyTavern.getContext();

unregisterFunctionTool('get_weather');
```

## 提示和技巧

1. 成功的工具调用会保存为可见聊天历史的一部分，并显示在聊天 UI 中，因此你可以检查实际的参数和结果。如果不希望这样，请在注册工具时设置 `stealth: true`。
2. 要使用自定义 CSS 美化或隐藏工具调用消息，请针对 `.mes` 元素上的 `toolCall` 类，例如 `.mes.toolCall { display: none; }` 或 `.mes.toolCall { opacity: 0.5; }`。
3. 为你的工具编写清晰、具体的描述——LLM 使用这些描述来决定何时以及如何调用它们。包括关于何时应使用工具的指导。
4. 保持参数模式简单且文档完善。每个属性的 `description` 有助于 LLM 填写正确的值。
5. 工具调用有递归限制（默认：5 轮）。如果 LLM 持续重复调用工具，执行将在达到限制后停止。