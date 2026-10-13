
# 上下文模板

> **📝 适用于：文本补全 API**
>
> 有关聊天补全 API 中的等效设置，请使用 [提示词管理器](/usage/prompts/prompt-manager/)。


通常，AI 模型要求你以某种特定方式向它们提供角色数据。SillyTavern 为不同模型内置了一系列预设转换规则，但你也可以根据自己的需要进行自定义。

在“[高级格式化](/usage/core-concepts/advancedformatting/)”面板中编辑这些设置。

## 故事字符串

此字段是提示词前言的模板（内部称为故事字符串）。这是为文本补全和指令模型添加 [角色卡](/usage/characters/) 中所定义信息的主要方式。

该模板支持 Handlebars 语法、自定义文本注入或格式化，以及任何其他[宏](/usage/core-concepts/macros/)。语言参考见：<https://handlebarsjs.com/guide/>

我们向 Handlebars 求值器提供以下参数（用双花括号包裹）：

1. `{{anchorBefore}}`：设置为使用“故事字符串之前”位置的提示词。
2. `{{anchorAfter}}`：设置为使用“故事字符串之后”位置的提示词。
3. `{{description}}`：角色的[描述](/usage/core-concepts/characterdesign/#character-description)。
4. `{{scenario}}`：角色的[场景](/usage/core-concepts/characterdesign/#scenario)。
5. `{{personality}}`：角色的[性格](/usage/core-concepts/characterdesign/#personality-summary)。
6. `{{system}}`：[系统提示词](/usage/core-concepts/advancedformatting/#system-prompt) 或角色的[主提示词](/usage/core-concepts/characterdesign/#prompt-overrides)覆盖（如果存在且在用户设置中启用了“优先使用角色提示词”）。
7. `{{persona}}`：所选[人设的描述](/usage/core-concepts/personas/#persona-description)。
8. `{{char}}`：角色的名称。
9. `{{user}}`：所选人设的名称。
10. `{{wiBefore}}` 或 `{{loreBefore}}`：位置设置为“角色定义之前”的已激活[世界信息](/usage/core-concepts/worldinfo/)条目的合并内容。
11. `{{wiAfter}}` 或 `{{loreAfter}}`：位置设置为“角色定义之后”的已激活[世界信息](/usage/core-concepts/worldinfo/)条目的合并内容。
12. `{{mesExamples}}`：（可选）角色的[示例对话](/usage/core-concepts/characterdesign/#examples-of-dialogue)，以指令格式编写并带有分隔符。
13. `{{mesExamplesRaw}}`：角色的[示例对话](/usage/core-concepts/characterdesign/#examples-of-dialogue)，以原始格式呈现，不带任何格式化。

> **💡 **重要****
>
> 在故事字符串中使用 `{{mesExamples}}` 时，请将 **<i class="fa-solid fa-user-cog"></i> 用户设置** 面板中的 **“示例消息行为”** 设置为 **“从不包含示例”**，以避免示例消息在提示词中重复出现。


支持一个特殊的 `{{trim}}` 宏，用于移除其周围的任何换行符。如果你希望文本的某部分不与上一行以换行符分隔，请使用它（_空格**不会**被移除_）。

**警告**：如果故事字符串模板中缺少上述任何参数，它们将完全不会随提示词发送。

### 提示词锚点

`{{anchorBefore}}` 和 `{{anchorAfter}}` 是通用占位符，用于放置由各种扩展和杂项功能添加到所选静态位置的提示词，例如：

* [作者注释](/usage/core-concepts/authors-note/)
* [总结](/extensions/summarize/)
* [聊天向量化](/extensions/chat-vectorization/) / [数据库](/usage/core-concepts/data-bank/)
* [STscript 注入](/usage/st-script/#prompt-injections)
* [网络搜索](/extensions/websearch/)

### 故事字符串位置

默认情况下，渲染后的故事字符串（所有占位符均已替换）被放置在提示词的最开头，后面紧跟示例消息和可见的聊天历史记录。

或者，你可以通过选择“聊天内 @ 深度”选项将其移动到动态位置，该选项将故事字符串放置在聊天上下文中的特定深度处。

> **⚠️ **注意****
>
> 如果模板包含用于包裹故事字符串的静态提示词元素（模型特定的前缀或后缀），使用“聊天内 @ 深度”位置将导致其被错误地用重复序列双重包裹，这可能会导致意外结果。
>
> 在这种情况下，你可以通过以下方式之一修复该问题：
>
> 1. **内置模板**：按照[高级格式化](/usage/core-concepts/advancedformatting/#resetting-templates)中描述的步骤将模板重置为默认值。
> 2. **自定义模板**：将静态元素从故事字符串模板移动到[故事字符串序列](/usage/core-concepts/instructmode/#sequences-story-string-wrapping)。


### 故事字符串包裹

> **📝 提示**
以下部分仅在**指令模式**开启时适用。
> **📝 提示**

* **默认**位置：渲染后的故事字符串将使用[故事字符串序列](/usage/core-concepts/instructmode/#sequences-story-string-wrapping)中定义的序列进行包裹。
* **聊天内 @ 深度**位置：渲染后的故事字符串将使用[聊天消息序列](/usage/core-concepts/instructmode/#sequences-chat-messages-wrapping)中为所选角色（默认：系统）定义的序列进行包裹。

## 示例分隔符

用作块标题以及示例对话块之间的分隔符。示例对话中任何 `<START>` 标签的实例都将被替换为此字段的内容。

## 聊天开始

在渲染后的故事字符串之后、示例对话块之后，但在上下文中的第一条消息之前，作为分隔符插入。

## 分隔符作为停止字符串

将“示例分隔符”和“聊天开始”添加到停止字符串列表中。

如果模型倾向于产生幻觉或泄露以分隔符开头的整块示例对话，这会很有帮助。

## 名称作为停止字符串

将角色和人设名称添加到停止字符串列表中。

建议保持开启以防止模型模仿。

## 始终将角色名称添加到提示词

> **ℹ️ Info**
>
> 当指令模式开启时，此设置无效。名称行为改由所选的[包含名称](/usage/core-concepts/instructmode/#include-names)选项定义。


将角色名称追加到提示词末尾，以强制模型以该角色的身份完成消息：

```txt
** 其他上下文内容 **
Character:
```