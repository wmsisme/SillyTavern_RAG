
# 快速入门

> **📌 Light**
>
> 我完全不懂。请直接告诉我最简单、最快速的方法来开始使用 SillyTavern。 -- *匿名用户*


你可以在几分钟内开始使用 SillyTavern。以下是两种简单的入门方式：

* 你可以免费[使用 AI Horde](#使用-ai-horde-快速入门)。AI Horde 是一个由社区驱动的 AI 服务，提供多种 AI 模型的访问权限。

* 如果你有 OpenAI 账户或想注册一个，可以[使用 OpenAI](#使用-openai-快速入门)。

## 使用 AI Horde 快速入门

1. 按照[安装指南](/installation/)安装并启动 SillyTavern。

2. 在 SillyTavern 的初始设置界面中，为你的角色输入一个名称。该名称将在聊天中使用。

   ![这是一段可选的说明文字](/static/quick-start/1_name.png)
3. 点击顶部栏的“API 连接”按钮。

   ![这是一段可选的说明文字](/static/quick-start/2_api_conn.png)
4. 输入 AI Horde 的 API 密钥。你可以暂时使用 `0000000000`，或者从 [AI Horde](https://aihorde.net/) 获取免费密钥。

   ![这是一段可选的说明文字](/static/quick-start/3_horde_key.png)
5. 选择要使用的 AI 模型。从列表顶部挑选几个即可。你之后随时可以更改。

   ![这是一段可选的说明文字](/static/quick-start/4_horde_models.png)
6. 关闭“API 连接”窗口。在底部的聊天框中输入一条消息，然后按 Enter 键。

   ![这是一段可选的说明文字](/static/quick-start/5_msg.png)
7. 稍等片刻，你的 AI 就会回复。你可以继续与它[聊天](/usage/chatting/)。大功告成！

   ![这是一段可选的说明文字](/static/quick-start/6_success.png)

## 使用 OpenAI 快速入门

### 安装 SillyTavern

按照[安装指南](/installation/)安装并启动 SillyTavern。

### 获取 OpenAI 访问权限

1. 注册 OpenAI。
2. 前往 <https://platform.openai.com>
3. 点击右上角的账户图标，然后选择“查看 API 密钥”。
4. 点击“创建新的密钥”。立即将密钥复制到安全位置。**请勿分享此密钥。任何拥有它的人都可以使用你的账户调用 GPT，费用由你承担。**

### 配置 SillyTavern 以使用你的 API

1. 在 SillyTavern 的顶部栏中，点击“API 连接”。
2. 在“API”下，选择“聊天补全（OpenAI）”。
3. 在“聊天补全源”下，选择“OpenAI”。
4. 粘贴上一步保存的 API 密钥。
5. 点击“连接”按钮。确认显示“有效”。
6. 默认情况下，SillyTavern 将使用 GPT-4 Turbo。你可以选择其他模型，但请先了解定价。

### 测试你的设置

1. 在 SillyTavern 的顶部栏中，点击最右侧的“角色管理”。
2. 选择一个现有角色，例如 Seraphina。
3. 在底部的文本框中，向 Seraphina 发送一些内容，然后按 Enter 键或点击“发送”按钮。

如果所有步骤正确，几秒钟后 Seraphina 就会回复。