
# 集成外部提供商

SillyTavern 通过多种不同的集成途径支持外部服务。在实现具名提供商之前，请先选择集成途径，以确保结果有适当的维护负责人，并且不会在现有通用接口已足够的情况下增加永久性的核心表面。

> **⚠️ Warning**
>
> 不要将已完成的拉取请求作为新具名提供商或服务的首次产品讨论。一个可用的实现本身并不能证明 SillyTavern 应当维护该集成。


## 选择集成途径

| 提案 | 推荐途径 |
| --- | --- |
| 修复或更新 SillyTavern 已支持的提供商 | 提交普通 issue 或拉取请求，附上复现和验证细节。 |
| 改善某一类 OpenAI 兼容服务的兼容性 | 针对通用 **Custom (OpenAI-compatible)** 路径提出提供商中立的 issue 或拉取请求。 |
| 添加模型路由器、经销商、重路由、网关或聚合器 | 为 **Custom (OpenAI-compatible)** 发布提供商自有的设置指南。仅在需要提供商特定行为时，才添加第三方 UI 扩展或服务器插件。 |
| 添加第一方模型提供商 | 先提交公开 issue，说明提供商自有的模型、SillyTavern 用例，以及为什么通用途径不够充分。 |
| 添加 TTS、语音、网络搜索、图像、向量化、嵌入、重排序或其他非聊天服务 | 先提交公开 issue，展示独立的 SillyTavern 用户需求、明确的产品优势、实时验证以及现实的维护负责人。 |

现有集成不构成添加新集成的先例。新的官方提供商集成属于例外情况，因为每个具名来源都会成为永久的 UI、认证、兼容性、测试、文档和支持表面。

## 对兼容的聊天提供商使用 Custom (OpenAI-compatible)

实现了 OpenAI Chat Completions API 的外部聊天提供商通常应使用 SillyTavern 现有的通用来源：

1. 打开 **API Connections**。
2. 选择 **Chat Completion**。
3. 选择 **Custom (OpenAI-compatible)** 作为来源。
4. 输入提供商的 API 根地址和 API 密钥。
5. 选择 `/v1/models` 返回的模型，或手动输入模型 ID。
6. 使用 **Test Message** 验证连接。

完整的用户说明、提示后处理选项和故障排除注意事项，请参阅 [Custom OpenAI-compatible endpoint](/usage/api-connections/openai/#custom-openai-compatible-endpoint)。

提供商应发布并维护自己的 SillyTavern 设置页面。提供商特定的端点 URL、账户步骤、模型目录、区域和兼容性说明会独立于 SillyTavern 发生变化，应留在拥有这些内容的服务方。SillyTavern 官方文档不是所有兼容商业端点的目录。

## 可复制的提供商设置指南

将此作为提供商自有文档的起点。替换所有占位符，并移除不支持的功能，而不是将猜测呈现为兼容性声明。

~~~md
# 将 <Provider> 与 SillyTavern 配合使用

## 前提条件

- 一个 <Provider> 账户
- 一个 API 密钥
- 一个模型 ID

## 连接

1. 在 SillyTavern 中，打开 **API Connections**。
2. 选择 **Chat Completion**。
3. 选择 **Custom (OpenAI-compatible)** 作为来源。
4. 输入 `<base URL>` 作为端点。使用 API 根地址，通常以 `/v1` 结尾，而不是 `/chat/completions`。
5. 输入你的 API 密钥。
6. 从获取的列表中选择一个模型，或手动输入 `<model ID format>`。
7. 如果提供商需要，选择 `<prompt post-processing setting>`。
8. 点击 **Test Message**。

## 功能支持

- 通过 `/v1/models` 发现模型：<yes/no/limitations>
- 流式传输：<yes/no/limitations>
- 工具调用：<yes/no/limitations>
- 视觉：<yes/no/limitations>
- 推理：<yes/no/limitations>
- 结构化输出：<yes/no/limitations>

## 已知限制

<列出提供商特定的兼容性说明和未测试的功能。>

## 支持

有关提供商 API、计费、账户或模型可用性问题，请联系 <provider support route>。

最后验证于 SillyTavern <version or commit>，日期 <date>。
~~~

设置指南记录的是兼容途径；它不是认可、不是完全兼容的保证，也不意味着将提供商支持转移给 SillyTavern 维护者。

## 为提供商特定设置构建第三方 UI 扩展

当提供商需要超出书面设置指南的便利性或提供商自有行为时，UI 扩展是合适的归属，例如：

- 引导式配置和连接测试；
- 提供商特定的可选设置；
- 模型展示或发现辅助工具；
- 账户、额度或用量链接；
- 请求头、请求字段或提示后处理的默认值；
- 能力和限制说明；或
- 提供商品牌和支持链接。

该扩展可以根据需要与 SillyTavern 现有的 UI、事件、上下文和请求路径集成。它仍然是第三方提供商自有的表面，因此扩展作者负责兼容性更新和用户支持。

阅读 [Writing UI Extensions](/for-contributors/writing-extensions/) 了解扩展结构、生命周期、设置、模板和当前 API 指南。

## 仅在需要服务器端行为时添加服务器插件

普通的 OpenAI 兼容服务不需要仅仅为了避免手动配置而使用服务器插件。当集成确实需要 Node 端行为时，才使用服务器插件，例如：

- 提供商特定的服务器端点；
- 无法在浏览器中安全进行的请求签名或凭证交换；
- 针对非 OpenAI 兼容 API 的协议转换；
- 服务器端代理或回调流程；或
- UI 扩展无法使用的 Node.js 依赖。

服务器插件不在沙箱中运行，必须由用户显式启用。当两者都需要时，将 UI 放在扩展中，将特权服务器行为放在插件中。在选择此途径之前，请阅读 [Writing Server Plugins](/for-contributors/server-plugins/)。

## 提出提供商中立的兼容性改进

具名集成可能揭示通用来源中的真实限制。当改进对一类兼容端点都有益时，请单独提出该限制。

提供商中立的提案应：

- 通过 **Custom (OpenAI-compatible)** 复现该行为；
- 描述受影响的 API 形态，而不仅仅是某一个品牌；
- 避免添加具名来源、固定提供商 URL、图标或提供商特定分支；
- 保留现有的兼容端点；以及
- 包含针对通用行为的聚焦验证。

即使 SillyTavern 不接受暴露问题的具名集成，提供商中立的改进仍然受欢迎。

## 在实现之前讨论官方集成

当具名来源能够以相称的方式增加通用和第三方途径无法提供的有意义能力、正确性或用户体验时，第一方提供商可能会被考虑进行官方集成。

对于第一方模型提供商，issue 应说明：

- 提供商开发和运营哪些有意义的模型；
- 具体的 SillyTavern 用例；
- 为什么 **Custom (OpenAI-compatible)** 不够充分；
- 所需的最小提供商特定表面；
- 维护者如何验证实时 API；以及
- 随着 API 变化，谁将维护该集成。

对于 TTS、语音、网络搜索、图像、向量化、嵌入、重排序、翻译及类似服务，issue 还必须展示独立的 SillyTavern 用户需求，以及在实现开始之前相对于现有来源的明确优势。

提交 issue、收集反馈、提供测试访问权限或提供长期维护承诺，都使提案值得讨论；但这些都不保证被接受。

## 保持所有权和支持的明确性

第三方提供商文档、扩展和插件应明确说明：

- 谁维护该集成；
- 用户在哪里报告提供商特定问题；
- 测试了哪些 SillyTavern 版本；
- 支持或不支持哪些提供商能力；
- 哪些数据和凭证会离开用户的安装环境；以及
- 说明最后验证的日期或版本。

SillyTavern 维护者可能会协助处理提供商中立的核心缺陷，但提供商账户、计费、API 可用性、模型目录和第三方集成支持仍由提供商或扩展作者负责。