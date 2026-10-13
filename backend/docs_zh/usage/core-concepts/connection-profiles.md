
# 连接配置文件

保存连接配置文件可快速在不同的 API、模型和格式化模板之间切换。当您活跃使用多个 API 连接，或需要在不同配置间切换而无需逐层浏览菜单时，此功能非常有用。

## 访问连接配置文件

从 SillyTavern 1.12.6 或更高版本开始，此功能作为内置扩展默认启用，并在 API 连接菜单中可用。如果您希望*禁用*它，请打开扩展面板，点击“管理扩展”，在列表中找到“连接配置文件”，取消勾选“已启用”复选框，然后点击“关闭”。

## 保存的内容

连接配置文件保存以下选择项。

### 通用

* [API 类型、模型和服务器 URL](/usage/api-connections/)
* [密钥](/usage/faq/#where-are-my-api-keys-stored-why-cant-i-see-them)
* [设置预设](/usage/common-settings/)
* [回复前缀](/usage/core-concepts/advancedformatting/#start-reply-with)（可明确为空）
* [自定义停止字符串](/usage/core-concepts/advancedformatting/#custom-stopping-strings)（可明确为空）
* [推理格式化](/usage/prompts/reasoning/#configuration)

### 文本补全 API

* [系统提示及其状态](/usage/core-concepts/advancedformatting/#system-prompt)
* [指令模式状态及模板](/usage/core-concepts/instructmode/)
* [上下文模板](/usage/core-concepts/advancedformatting/#context-template)
* [分词器](/usage/core-concepts/advancedformatting/#tokenizer)

### 聊天补全 API

* [提示后处理](/usage/api-connections/openai/#prompt-post-processing)
* 代理预设

## 管理连接配置文件

> **ℹ️ 注意**
>
> 配置文件只保存下拉字段中的选择，并不了解底层设置的详细信息。这意味着切换到不同配置文件时，您将丢失未保存的更改。为防止这种情况，如果您不想丢失临时更改，请确保更新所有预设和模板。


* 要保存配置文件，请设置所有必要的设置，然后点击“创建”按钮。接着检查设置并为配置文件提供一个名称。**名称必须唯一。**
* 要查看所选配置文件的详细信息，请点击“信息”按钮。再次点击可隐藏详细信息。
* 连接配置文件设置会保存到 `settings.json` 中，但在您点击“更新”按钮之前，不会更改关联的配置文件保存文件。这意味着，如果您设置了一个配置文件，然后在未更新的情况下切换到另一个，您将丢失之前的所有更改。
* 要从已保存的配置文件中恢复更改后的选择，请点击“重新加载”按钮。
* 要删除配置文件，请点击“删除”按钮并确认删除。**此操作不可撤销。**

## 斜杠命令

连接配置文件可以通过以下斜杠命令进行管理。

1. `/profile [name]` - 如果提供了参数，则切换到该配置文件；否则获取当前配置文件的名称。
2. `/profile-create [name]` - 将当前设置保存为具有指定名称的新配置文件。
3. `/profile-list` - 返回一个 JSON 序列化的可用配置文件名称数组。
4. `/profile-get [name]` - 获取指定名称配置文件的详细信息，以 JSON 序列化对象形式返回。
5. `/profile-update` - 使用当前设置更新所选配置文件。