
# 网页搜索

将网页搜索结果添加到 LLM 提示中。

> **📝 注意**
>
> 某些 [聊天补全](/usage/api-connections/openai/) 源提供了内置的网页搜索功能。在这种情况下，此扩展将基本冗余。请检查 **<i class="fa-solid fa-sliders"></i> AI 响应配置** 面板中的“启用网页搜索”开关。例如，这项功能在 Claude、Google AI Studio / Vertex AI、OpenRouter、Chutes 以及其他后端中可用。


## 可用来源

### Selenium 插件

需要安装并启用官方服务器插件。

详情请参见 [SillyTavern-WebSearch-Selenium](https://github.com/SillyTavern/SillyTavern-WebSearch-Selenium)。

支持 Google 和 DuckDuckGo 搜索引擎。

### Extras API

需要主机上安装 `websearch` 模块以及 Chrome/Firefox 网页浏览器。

支持 Google 和 DuckDuckGo 搜索引擎。

### SerpApi

需要 API 密钥。

在此处获取密钥：<https://serpapi.com/dashboard>

### SearXNG

需要 SearXNG 实例 URL（私有或公共均可）。使用 HTML 格式获取搜索结果。

SearXNG 首选项字符串：从 SearXNG - 首选项 - COOKIES - 复制首选项哈希获取。

了解更多：<https://docs.searxng.org/>

### Tavily AI

需要 API 密钥。

在此处获取密钥：<https://app.tavily.com/>

### KoboldCpp

必须在文本补全 API 设置中提供 KoboldCpp URL。KoboldCpp 版本需 >= 1.81.1，并且启动时必须启用 WebSearch 模块：在 GUI 启动器中启用网络 => 启用 WebSearch，或在命令行中添加 `--websearch`。

参见：<https://github.com/LostRuins/koboldcpp/releases/tag/v1.81.1>

### Serper

需要 API 密钥。

在此处获取密钥：<https://serper.dev/>

### Z.AI

需要 API 密钥，请先在聊天补全 API 设置中设置。与 Coding API 订阅不兼容！

在此处获取密钥：<https://z.ai/manage-apikey/apikey-list/>

文档：<https://docs.z.ai/api-reference/tools/web-search>

## 如何使用

1. 确保你使用的是最新版本的 SillyTavern。
2. 通过 SillyTavern 中的“下载扩展和资源”菜单安装扩展。
3. 打开“网页搜索”扩展设置，设置你的 API 密钥或连接到 Extras，并启用扩展。
4. 在你聊天时，网页搜索结果会自然地被添加到提示中。**只有用户消息会触发搜索。**
5. 为了更自然地包含搜索结果，请将搜索查询用反引号括起来：```告诉我关于 `瑞恩·高斯林最新电影` 的信息。``` 将生成搜索查询 `瑞恩·高斯林最新电影`。
6. 可选地，根据你的喜好配置设置。

## 设置

### 通用

1. 已启用 - 打开或关闭扩展。
2. 来源 - 设置搜索结果来源。
3. 缓存生命周期 - 搜索结果在你的提示中缓存的时间（以秒为单位）。默认 = 一周。

### 提示设置

1. 提示预算 - 设置插入文本的最大容量（以字符数计，而非 Token）。经验法则：1 Token ≈ 3-4 个字符，根据模型上下文限制进行调整。默认 = 1500 个字符。
2. 插入模板 - 结果如何被插入到提示中。支持常规宏 + 特殊宏：\ \ \{\{query\}\} 用于搜索查询，\ \ \{\{text\}\} 用于搜索结果。
3. 注入位置 - 结果在提示中的位置。与作者注记的选项相同：作为聊天内注入或系统提示之前/之后。

### 搜索激活

1. 使用函数工具 - 使用 [函数调用](/for-contributors/function-calling/) 来激活搜索或抓取网页。必须使用支持的聊天补全 API，并在 AI 响应设置中启用。**启用后，会禁用所有其他激活方法。**
2. 使用反引号 - 启用通过用单个反引号括起来的词语来激活搜索。
3. 使用触发短语 - 启用通过触发短语来激活搜索。
4. 正则表达式 - 提供一个 JavaScript 风格的正则表达式来匹配用户消息。如果正则匹配，将使用给定的查询触发搜索。搜索查询支持 `\{\{macros\}\}` 和 $1 语法来引用匹配的组。示例：`/what is happening in (.*)/i` 正则表达式，搜索查询为 `news in $1`，将匹配包含 `what is happening in New York` 的消息，并以查询 `news in New York` 触发搜索。
5. 触发短语 - 逐个添加会触发搜索的短语。它可以出现在消息的任何位置，查询从触发词开始，总共覆盖到“最大词数”。若要排除特定消息不进行处理，该消息必须以句点开头，例如 `.What do you think?`。触发器的优先级：首先按文本框中的顺序，然后按用户消息中第一个出现的顺序。
6. 最大词数 - 搜索查询中包含的单词数量（包括触发短语）。Google 限制每个提示大约 32 个单词。默认 = 10 个单词。

### 页面抓取

1. 访问链接 - 将从访问的搜索结果页面中提取文本，并保存到文件附件中。
2. 访问数量 - 将访问并解析文本的链接数量。
3. 访问域名黑名单 - 排除访问的网站域名。每行一个。
4. 文件头 - 文件头模板，插入到文本文件开头，包含额外的 \{\{query\}\} 宏。
5. 块头 - 链接块模板，与每个链接的解析内容一起插入。使用 \{\{link\}\} 宏表示页面 URL，使用 \{\{text\}\} 宏表示页面内容。
6. 保存目标 - 保存抓取结果的位置。可选选项：触发消息附件，或数据银行的聊天附件，或仅图像（如果来源支持）。
7. 包含图像 - 将相关图像附加到聊天中。需要支持图像的来源（见下文）。

## 更多信息

来自最新查询的搜索结果将一直包含在提示中，直到找到下一个有效查询。
如果你想提出额外问题而不意外触发搜索，请在消息开头加一个句点。

> **ℹ️ Info**
>
> 如果启用且可用，网页搜索函数工具总是覆盖其他触发器。


触发器优先级（如果启用了多个）：

1. 反引号。
2. 正则表达式。
3. 触发短语。

要丢弃之前的所有查询而不处理，用户消息以感叹号开头，例如用户消息 `!现在我们来谈谈...` 将丢弃此消息及其之前的所有消息。

此扩展还提供了一个 `/websearch` 斜杠命令，可在 STscript 中使用。更多信息在此：[STscript 语言参考](/usage/st-script/#extension-commands)

```stscript
/websearch (links=on|off snippets=on|off [query]) – 执行网页搜索查询。使用命名参数指定返回内容 - 页面摘要（默认：on）、完整解析页面（默认：off）或两者。

示例：/websearch links=off snippets=on how to make a sandwich
```

### 搜索结果中可以包含哪些内容？

**词库：**

- 答案框：对问题的直接回答。
- 知识图谱：关于该主题的百科知识。
- 页面摘要：来自网页的相关摘录。
- 相关问题：类似主题的问题和答案。
- 图像：相关图像。

#### SerpApi

1. 答案框。
2. 知识图谱。
3. 页面摘要（最多 10 条）。
4. 相关问题（最多 10 条）。
5. 图像（最多 10 张）。

#### Selenium 插件和 Extras API

1. Google - 答案框、知识图谱、页面摘要。
2. DuckDuckGo - 页面摘要。

**Selenium 插件** 还可以额外提供图像。

#### SearXNG

1. 信息框。
2. 页面摘要。
3. 图像。

#### Tavily AI

1. 答案。
2. 页面内容。
3. 图像（最多 5 张）。

#### KoboldCpp

1. 页面标题。
2. 页面摘要。

#### Serper

1. 答案框。
2. 知识图谱。
3. 页面摘要。
4. 相关问题。
5. 图像。

#### Z.AI

1. 页面标题。
2. 页面摘要。