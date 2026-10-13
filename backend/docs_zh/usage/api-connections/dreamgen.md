
# DreamGen

DreamGen 是一个用于 AI 驱动的角色扮演和故事创作的应用程序和 API。他们提供免费套餐，以及付费订阅，允许无限量使用其高质量的内部文本生成模型，这些模型专门用于可引导的 AI 角色扮演和故事创作。创建一个账户开始使用：<https://dreamgen.com/>。

（免费）积分在每个日历月开始时重置。请参阅 [定价页面](https://dreamgen.com/pricing) 了解每个模型的积分消耗，以及 [使用页面](https://dreamgen.com/account/usage) 查看您的剩余积分。

## 连接 DreamGen

### 获取 API 密钥

前往 [DreamGen API 密钥](https://dreamgen.com/account/api-keys) 页面，点击“新建 API 密钥”按钮。确保 API 密钥已复制到剪贴板。

![创建新的 DreamGen API 密钥](/static/dreamgen/dreamgen_api_keys_new.jpg)
![复制 DreamGen API 密钥](/static/dreamgen/dreamgen_api_keys_copy.jpg)

### 连接

1. 前往 SillyTavern 连接设置。
2. 选择 API：文本补全
3. 选择 API 类型：DreamGen
4. 输入 API 密钥
5. （可选）选择一个模型

![连接到 DreamGen](/static/dreamgen/dreamgen_st_connection.png)

## 模型

DreamGen API 提供了几种不同规模的模型。

- Lucid Max（在 API 中称为 `lucid-v1-max` 或 `lucid-v1-extra-large`）
- Lucid Base（在 API 中称为 `lucid-v1-base` 或 `lucid-v1-medium`）——对应权重可用的 [Lucid V1 Nemo](https://dreamgen.com/docs/models/lucid-v1/huggingface)。

Lucid Base 消耗的积分少得多，速度更快，而 Lucid Max 更具创造力，能够处理更复杂的指令和叙述。

## 设置

Lucid V1 DreamGen 模型使用了针对角色扮演和写作优化的 Llama 3 聊天模板扩展。它们与特定的系统提示配合使用效果最佳。

我们强烈建议从以下之一的主预设开始：

- 确保启用了指令模式，并在导入时选中所有复选框。
- [DreamGen Lucid V1 角色扮演预设](https://dreamgen.com/docs/models/lucid-v1/sillytavern/master-preset/role-play)
- [DreamGen Lucid V1 故事预设](https://dreamgen.com/docs/models/lucid-v1/sillytavern/master-preset/story)

这些预设内置了对 `/sys` 的支持，用于向模型发送指令。您可以使用这些指令来引导剧情或控制角色的行为。

![选中 DreamGen 预设](/static/dreamgen/dreamgen_st_preset.png)

其他资源：

- [**详细的 DreamGen + SillyTavern 指南**](https://dreamgen.com/docs/models/lucid-v1/sillytavern)
- [详细的 Lucid V1 提示格式文档](https://dreamgen.com/docs/models/lucid-v1)。
- [DreamGen + SillyTavern 角色扮演演示](https://imgur.com/a/dreamgen-lucid-sillytavern-roleplay-demo-bhzQpto)
- [DreamGen + SillyTavern 故事创作演示](https://imgur.com/a/dreamgen-lucid-sillytavern-writing-demo-JLv5iO3)
- [创建自己的场景的技巧](https://v2.dreamgen.com/docs/scenario-editor)

## 常见问题

### 如何让回复更长或更短？

您可以在格式预设中设置 `Last Assistant Prefix`。

对于长消息：

```txt
<|start_header_id|>user<|end_header_id|>

The next message is from {{char}} and is at least 100 words long<|eot_id|><|start_header_id|>writer character {{char}}<|end_header_id|>

```

对于短消息：

```txt
<|start_header_id|>user<|end_header_id|>

The next message is from {{char}} and is at most 50 words long<|eot_id|><|start_header_id|>writer character {{char}}<|end_header_id|>

```

确保保留所有换行符，包括末尾的两个。

![长消息前缀](/static/dreamgen/dreamgen_st_long_response_prefix.png)

您也可以在卡片或系统提示中包含写作风格描述，例如：

```txt
## Style

<your description>
```

请参阅 [“风格”文档](https://v2.dreamgen.com/docs/scenario-editor#style) 以了解更多信息并查看一些示例。

### 如何引导角色扮演/故事？

使用 `/sys` 选项向模型发送指令。一些示例：

> 旅店老板给达莉亚和其他人每人倒了一品脱麦芽酒。

> 下一段消息来自德拉科，应至少 200 字，重点描述他对这个决定的内在冲突。

[查看实际效果。](https://imgur.com/a/dreamgen-lucid-sillytavern-roleplay-demo-bhzQpto)