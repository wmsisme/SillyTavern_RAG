
# 提示词

当你向 AI 发送消息时，你输入的文本会与其他文本组合成一个单一的请求发送给 AI。这个组合后的文本被称为“提示词”，有时也称为“请求”或“上下文”。

提示词可以包含多种不同类型的文本，包括：

* 给 AI 的[主要指令](#主要提示词系统提示词)，说明如何生成回复
* [AI 应扮演的角色定义](/usage/core-concepts/characterdesign/)
* [你所扮演的角色定义](/usage/core-concepts/personas/)
* [AI 所处“世界”的信息](/usage/core-concepts/worldinfo/)
* 来自[数据库](/usage/core-concepts/data-bank/)的相关文档或信息
* 过去对话的[摘要](/extensions/summarize/)
* [网络搜索](/extensions/websearch/)或其他[外部数据源](/for-contributors/function-calling/)的结果
* 对话中的历史消息
* **你发送给 AI 的消息**
* 给 AI 的[最终指令](#历史后指令)，说明如何生成回复

这些内容可能很多，管理起来可能很复杂！为了帮助你理解如何组织和修改发送给 AI 的请求，SillyTavern 识别了你可能想要包含在提示词中的不同元素。你可以据此构建提示词，包含适合你与 AI 交互方式的内容。

其中许多元素会在你修改它们的相关章节中进行说明。例如，要描述你希望 AI 扮演的角色，你可以使用[角色设计](/usage/core-concepts/characterdesign/)中的[描述](/usage/core-concepts/characterdesign/#personality-summary)字段。

## 查看提示词

阅读发送给 AI 的最终提示词，对于理解 AI 收到了什么信息以及它为什么生成那样的回复非常有帮助。你可以通过以下几种方式查看提示词：

* 使用 AI 回复消息上的提示词逐项分解图标
* 使用 [Prompt Inspector](https://github.com/SillyTavern/Extension-PromptInspector) 扩展
* 查看你运行 SillyTavern 的终端窗口中的日志
* 查看浏览器开发者工具中的控制台

## 更改提示词的构建方式

以正确的方式向 AI 呈现提示词的所有部分，对于获得最佳回复至关重要。你可以控制提示词的构建方式。

+++ 文本补全 API

使用[高级格式化](/usage/core-concepts/advancedformatting/)面板来自定义文本补全 API 的提示词构建。

+++ 聊天补全 API

使用[提示词管理器](/usage/prompts/prompt-manager/)来自定义聊天补全 API 的提示词构建。

+++

## 主要提示词（系统提示词）

主要提示词（或系统提示词）定义了模型应遵循的一般指令。它设定了对话的基调和上下文。例如，它告诉模型要充当 AI 助手、写作伙伴或虚构角色。

+++ 文本补全 API

[系统提示词](/usage/core-concepts/advancedformatting/#system-prompt)是[故事字符串](/usage/prompts/context-template/#story-string)的一部分，通常是模型收到的提示词的第一部分。

+++ 聊天补全 API

主要提示词是[提示词管理器](/usage/prompts/prompt-manager/)中的默认提示词之一。它通常是模型收到的上下文中的第一条消息，归属于（“发送自”）系统角色。

+++

默认的主要提示词为：

> Write \{\{char\}\}'s next reply in a fictional chat between \{\{char\}\} and \{\{user\}\}.

其中的 \{\{char\}\} 和 \{\{user\}\} 占位符会被替换为你在对话中定义的角色和人设名称。

你可以在主要提示词中使用任何受支持的 [\{\{宏\}\}](/usage/core-concepts/macros/) 标签，以包含可能因对话而异或随对话进展而变化的信息。

### 调整主要提示词

默认的主要提示词帮助模型理解它应该如何处理后续的角色和人设信息、如何解读过去的对话，以及生成什么样的回复。它是一个灵活的通用提示词，适用于许多场景，因为它确立了 AI 是以角色身份在与你的用户人设进行对话。

不过，你可以调整主要提示词以更好地满足你的需求。以下是一些常见的调整主要提示词的原因：

* **提供额外指令**：例如，你希望 AI 解释其推理过程、遵循特定规则或避免某些话题
* **明确 AI 的角色**：例如，你希望 AI 充当叙述者、故事讲述者或引导者
* **改变对话的上下文**：例如，你希望 AI 像 AI 助手、文字冒险游戏或写作伙伴那样回复

> **📝 尝试各种方法，看看哪种最适合你**
>
> 本指南中的所有示例对其他用户都很有效，但适合你需求和你所用模型的提示词可能会有所不同。尝试不同的指令和提示风格，看看哪种最适合你。如果你不确定该尝试什么，随时可以在 [SillyTavern Discord](https://discord.gg/sillytavern) 中寻求帮助。


在主要提示词中给 AI 提供额外指令，可以帮助它理解你想从对话中获得什么。

> Write one reply only. Write at least one paragraph, up to four.

> Markdown is enabled. Use it to format your response. Enclose code snippets in triple backticks.

> Write character dialogue in quotation marks. Write \{\{char\}\}'s thoughts in parentheses.

> You are an anime roleplay generation model for users aged 13 to 17. You always generate fun, age-appropriate responses.

> Answer truthfully and write out your thinking step by step to be sure you get the right answer.

AI 更容易遵循关于“应该做什么”的指令，而不是“不应该做什么”。例如，如果你希望 AI 避免某种写作方式，最好告诉它你希望它怎么写。虽然 *“不要决定 \{\{user\}\} 说什么或做什么”* 常被包含在提示词中以防止 AI 控制你的人设，但有些用户发现 *“以尊重 \{\{user\}\} 自主权的方式撰写 \{\{char\}\} 的回复”* 更有效。

关于用户或角色的信息、修改角色的写作和说话风格，或其他具体指令，通常有比主要提示词更合适的位置。主要提示词最适合用于关于整个对话的一般性指令，或关于你想进行的某类对话的指令。

### 消息历史的影响

在调整主要提示词以改善 AI 回复时，请注意 AI 会从消息历史中获取大量信息。历史记录是它对过去事件、角色互动和关系的记忆，也是它选择用词和写作风格的风格指南。

利用这一点，同时提供[示例消息](/usage/core-concepts/characterdesign/#examples-of-dialogue)来展示你希望 AI 如何回复。展示你想要的效果通常比试图解释它更容易！

当你的对话已经有历史记录时，更改主要提示词对 AI 回复的影响有限。在事件和关系方面，AI 会认为主要提示词发生在遥远的过去，而消息历史会更新它。在写作风格和用词方面，AI 会认为历史中的所有消息都是根据*当前*主要提示词中的规则生成的，并且它应该继续以同样的方式生成消息。以下是一些应对建议：

* 在当前指令靠近消息历史末尾或之后插入，例如使用[作者注释](/usage/core-concepts/authors-note/)
* 通过开始新对话来测试你对主要提示词的更改
* 编辑消息历史以删除或纠正不想要的行为示例
* 使用[历史后指令](#历史后指令)向 AI 提供最终指令

> **📝 第一次就做对！**
>
> 绝不要让 AI “蒙混过关”做出你不希望它做的事。如果你不喜欢 AI 的回复，不要当作它是正确的那样继续对话。相反，修改提示词、重新生成消息，然后从那里继续。这将帮助 AI 了解你想要什么。


### 移除“虚构聊天”上下文

在某些情况下，“虚构聊天”可能不是你的对话的正确上下文。

你可以从主要提示词中移除“虚构”上下文：

> Write \{\{char\}\}'s next reply in a conversation with \{\{user\}\}.

你可能根本不希望 AI 认为自己在角色扮演。与其移除角色的概念，你可以移除 AI 的概念：

> You are \{\{char\}\}, a helpful assistant. You provide useful information and help \{\{user\}\} with their questions.

### AI 作为叙述者或故事讲述者

如果你希望 AI 充当叙述者，从全知视角描述事件，创造自己的角色和设定，该怎么办？

一种方法是为 AI 创建一个命名角色作为叙述者。这个角色可以叫“Narrator”或“AI”，暗示 AI 是通用故事讲述者；也可以以特定场景或设定命名，赋予 AI 在该设定中叙述故事的任务。然后可以在[角色](/usage/core-concepts/characterdesign/)或[世界信息](/usage/core-concepts/worldinfo/)中定义设定的细节。

你需要调整默认的主要提示词以反映 AI 的角色。对于通用叙述者，你可以使用：

> You are \{\{char\}\}, a skilled and versatile storyteller. Narrate the story.

或者对于特定设定：

> You are the narrator of a fantasy scenario. Play as the characters that visit \{\{char\}\}.

明确用户在对话中的角色会有所帮助。你的消息是故事的一部分，还是给叙述者关于你角色做什么或说什么的指令？一个将用户纳入故事的示例：

> The story should progress by responding to the actions and dialogue of \{\{user\}\}. Narrate the story in third person.

一个将用户排除在故事之外的示例：

> Enter Adventure Mode. Narrate the story based on \{\{user\}\}'s dialogue and actions after ">". Describe the surroundings in vivid detail. Be detailed, creative, verbose, and proactive. Move the story forward by introducing fantasy elements and interesting characters.

定义用户的角色不仅有助于 AI 理解如何回复你的消息，还能帮助它了解在多大程度上可以控制你的人设。这可以避免 AI 替你的人设做出你更愿意自己决定的事情。

## 历史后指令

历史后指令（PHI）是在主要提示词和用户消息之后发送给 AI 的附加指令。它们可用于根据消息历史向 AI 提供额外的上下文或指令。

由于历史后指令是在用户消息之后发送的，它们是 AI 在生成回复前收到的最终指令。AI 通常会给它们比主要提示词更高的优先级，它们可以覆盖主要提示词的指令。

要使用按角色设置的历史后指令，请将它们添加到角色的[历史后指令](/usage/core-concepts/characterdesign/)中，并启用[优先使用角色指令](/usage/user-settings/)。要在使用角色特定指令的同时保留全局定义的 PHI，你可以在角色的历史后指令字段中使用 `{{original}}` 宏。

+++ 文本补全 API

历史后指令在[高级格式化](/usage/core-concepts/advancedformatting/)面板的系统提示词类别下定义。历史后指令作为一条不可见的用户角色注入添加在提示词最后一行（通常包含回复消息“头部”）之前。请注意，“启用系统提示词”开关必须开启，历史后指令才会生效（即使系统提示词本身为空）。

+++ 聊天补全 API

历史后指令是[提示词管理器](/usage/prompts/prompt-manager/)中的默认提示词之一。它通常是模型收到的上下文中的最后一条消息，归属于（“发送自”）系统角色。如果你的聊天补全 API 不支持系统角色，它通常会改为归属于用户角色。

+++

## 添加到提示词（世界信息）

你可以使用[世界信息](/usage/core-concepts/worldinfo/)功能在提示词的任何位置插入额外信息。通过设置信息应被插入的条件，你可以引导 AI 包含特定细节、改变回复方式或向对话中添加新元素。

世界信息的一些常见用途包括：

* 包含世界或设定信息的“设定集”或“百科全书”
* 为各种角色和情境管理不同系统提示词的方式
* 存储 AI 应在对话中“回忆”的记忆的地方
* 用于创建、编辑和分享角色细节的更模块化系统
* 随机事件和惊喜的来源，供 AI 做出反应，或让你做出反应！