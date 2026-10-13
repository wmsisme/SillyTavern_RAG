
# 高级格式化

本节提供的设置允许对[提示构建](/usage/prompts/)策略进行更多控制，主要针对文本补全 API。

此面板中的大多数设置不适用于聊天补全 API，因为这些 API 由提示管理器系统管理。

+++ 文本补全 API
* [系统提示](#系统提示)
* [上下文模板](#上下文模板)
* [分词器](#分词器)
* [自定义停止字符串](#自定义停止字符串)
+++ 聊天补全 API
* 系统提示：不适用，请使用[提示管理器](/usage/prompts/prompt-manager/)
* 上下文模板：不适用，请使用[提示管理器](/usage/prompts/prompt-manager/)
* [分词器](#分词器)
* [自定义停止字符串](#自定义停止字符串)
+++

## 重置模板

您可以将默认模板恢复为原始状态。可以通过 UI 或手动删除相关数据文件来实现。

### UI 重置

1. 打开 **<i class="fa-solid fa-font"></i> 高级格式化** 菜单。
2. 选择要重置的模板。
3. 点击 **<i class="fa-solid fa-recycle"></i> 恢复当前模板** 按钮。
4. 在提示时确认操作。

### 手动重置

> **📝 提示**
确保 `config.yaml`（参见[数据配置](/administration/config-yaml/#数据配置)）中的 `skipContentCheck` 设置为 `false`，否则不会触发内容检查。
> **📝 提示**

1. 导航到您的用户数据目录（详情请参见[数据路径](/installation/#数据路径)）。
2. 从用户数据目录的根目录删除 `content.log` 文件。该文件记录为您用户复制的默认文件。
3. 从相关子目录（`context`、`instruct`、`sysprompt` 等）中删除模板 JSON 文件。
4. 重新启动 SillyTavern 服务器。应用程序将重新填充默认内容，恢复任何已删除的默认模板。

## 后端定义的模板

> **📝 适用于：文本补全 API**
>
> 不适用于聊天补全 API，因为它们使用不同的提示构建器。


某些文本补全源提供自动选择模型作者推荐模板的能力。这是通过将模型 `tokenizer_config.json` 文件中定义的聊天模板的哈希值与 SillyTavern 的默认模板之一进行比较来实现的。

1. **<i class="fa-solid fa-bolt"></i> 派生模板** 选项必须在 **<i class="fa-solid fa-font"></i> 高级格式化** 菜单中启用。这可以应用于上下文、指令或两者。
2. 必须选择受支持的后端作为文本补全源。目前只有 llama.cpp 和 KoboldCpp 支持派生模板。
3. 在建立与 API 的连接时，模型必须正确报告其元数据。如果不起作用，请尝试将后端更新到最新版本。
4. 报告的聊天模板哈希值必须与[已知的 SillyTavern 模板](https://github.com/SillyTavern/SillyTavern/blob/release/public/scripts/chat-templates.js)之一匹配。这仅涵盖默认模板，例如 Llama 3、Gemma 2、Mistral V7 等。
5. 如果哈希值匹配，且模板存在于模板列表中（即未重命名或删除），则会自动选择该模板。

## 系统提示

> **📝 适用于：文本补全 API**
>
> 对于聊天补全 API 中的等效设置，请使用[提示管理器](/usage/prompts/prompt-manager/)。**主要提示**相当于聊天补全 API 中的系统提示。


系统提示定义模型要遵循的一般指令。它为对话设定基调和上下文。例如，它告诉模型扮演 AI 助手、写作伙伴或虚构角色。

系统提示是[故事字符串](/usage/prompts/context-template/#故事字符串)的一部分，并且通常是模型接收到的提示的第一部分。

请参阅[提示指南](/usage/prompts/#主要提示系统提示)以了解有关系统提示的更多信息。

## 上下文模板

> **📝 适用于：文本补全 API**
>
> 对于聊天补全 API 中的等效设置，请使用[提示管理器](/usage/prompts/prompt-manager/)。


通常，AI 模型要求您以某种特定方式向它们提供角色数据。SillyTavern 为不同模型提供了一个预定义的转换规则列表，但您可以根据需要自定义它们。

本部分的选项在[上下文模板](/usage/prompts/context-template/)中说明。

## 分词器

分词器是一种将文本分解为称为标记（tokens）的更小单元的工具。这些标记可以是单个单词，甚至是单词的一部分，例如前缀、后缀或标点符号。经验法则是，一个标记通常对应 3~4 个字符的文本。

本部分的选项在[分词器](/usage/prompts/tokenizer/)中说明。

## 自定义停止字符串

接受一个 JSON 序列化的停止字符串数组。示例：`["\n", "\nUser:", "\nChar:"]`。如果您不确定格式，请使用[在线 JSON 验证器](https://jsonlint.com/)。如果模型输出**以**任何停止字符串结尾，则会从输出中将其删除。

支持的 API：

1. KoboldAI Classic（1.2.2 及更高版本）或 KoboldCpp
2. AI Horde
3. 文本补全 API：Text Generation WebUI (ooba)、Tabby、Aphrodite、Mancer、TogetherAI、Ollama 等
4. NovelAI
5. OpenAI（最多 4 个字符串）及兼容 API
6. OpenRouter（文本和聊天补全）
7. Claude
8. Google AI Studio
9. MistralAI

## 以...开始回复

> **📝 注意**
>
> 默认情况下，“以...开始回复”的前缀不会显示在结果消息中。启用“在聊天中显示回复前缀”以显示它。


### 文本补全 API

预填充提示的最后一行，强制模型从该点继续。这对于强制内容很有用，例如使用定义的前缀推动[模型推理](/usage/prompts/reasoning/)：

```txt
<think>
当然！
```

### 聊天补全 API

在提示的末尾添加一个助手角色消息。对于某些后端模型，这相当于预填充模型响应，但有些可能根本不支持，并且会因验证错误而失败。如果不确定，请将此字段留空。