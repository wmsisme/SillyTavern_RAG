
# Google Gemini

Gemini 是 Google 尖端的多模态 LLM，可通过多个 API 使用，包括 Google Vertex AI 和 Google AI Studio（原 MakerSuite）。本指南将帮助您在 SillyTavern 中配置 Gemini API 连接。

## Google AI Studio

AI Studio 是试用最新 Google AI 模型最快、最用户友好的方式，无需设置 Google Cloud Platform (GCP) 项目。它提供一个简单的 API 密钥，可用于访问 Gemini 模型。

### 步骤 1：创建 Google AI Studio 密钥

1. 访问 [Google AI Studio](https://aistudio.google.com/apikey) 页面，使用您的 Google 账号登录。
2. 点击“获取 API 密钥”，接受条款和条件。
3. 点击“创建 API 密钥”生成您的 API 密钥。
4. 将 API 密钥复制到剪贴板。

### 步骤 2：将 API 密钥填入 SillyTavern

1. 在 SillyTavern 中，进入“API 连接”页面。
2. 选择“聊天补全”作为 API 类型。
3. 从下拉菜单中选择“Google AI Studio”。
4. 将您之前复制的 API 密钥输入到“API 密钥”文本框中。
5. 点击“连接”按钮保存密钥。

现在您应该能够将 Google AI Studio API 与 SillyTavern 一起使用了。

## Google Vertex AI

Vertex AI 是 Google Cloud Platform (GCP) 提供的一项服务。它可以访问各种 AI 模型，包括 Gemini 系列。

Vertex AI API 的设置有多种方式，可用的模型可能因使用方法而异。

### 服务账号

Google Cloud Platform (GCP) 要求使用服务账号来访问 Vertex AI，简单的 API 密钥无法使用。将从服务账号 JSON 文件中生成一个令牌，该令牌将用于向 Vertex AI API 验证请求。

您可以按照以下步骤创建服务账号：

**先决条件：**

1. 您必须拥有一个 Google Cloud Platform (GCP) 账号。
2. 您必须在 GCP 账号内创建一个项目。
3. 您必须为该项目启用结算功能。

#### 步骤 1：启用 Vertex AI API

在密钥生效之前，必须为项目启用该 API。

1. 访问 Google Cloud 控制台：<https://console.cloud.google.com/>
2. 确保顶部栏中选中了正确的项目。
3. 导航到 Vertex AI API 页面：<https://console.cloud.google.com/apis/library/aiplatform.googleapis.com>
4. 如果尚未启用，请点击“启用”按钮。

#### 步骤 2：创建服务账号

这是用于访问 Vertex AI API 的身份。

1. 在 Google Cloud 控制台中，导航到“服务账号”页面。您可以在顶部搜索栏中搜索，或使用以下直接链接：<https://console.cloud.google.com/iam-admin/serviceaccounts>
2. 选择您的 GCP 项目，点击“+ 创建服务账号”。
3. 服务账号名称：为其指定一个描述性名称，例如 `my-vertex-ai-client`。
4. 点击“创建并继续”。
5. 授予此服务账号对项目的访问权限：在“角色”下拉菜单中，搜索并选择“Vertex AI 用户”。此角色授予运行模型所需的权限，同时不会授予过多访问权限。
6. 点击“继续”，然后点击“完成”。

#### 步骤 3：生成 JSON 密钥

这是您需要的“密码”文件。它包含敏感信息，因此请勿分享或将其上传到任何公共位置。

1. 您现在应该已返回服务账号列表。找到您刚刚创建的账号（例如 sillytavern-vertex-ai）。
2. 点击该行最右侧的三点菜单 (⋮)，选择“管理密钥”。
3. 点击“添加密钥” -> “创建新密钥”。
4. 确保密钥类型设置为 JSON。
5. 点击“创建”。

一个 .json 文件将立即下载到您的计算机。请妥善保管，因为该密钥丢失后无法恢复。

#### 步骤 4：将 JSON 内容填入 SillyTavern

您下载的 JSON 文件包含向 Vertex AI API 进行身份验证所需的所有信息。其内容类似如下：

```json
{
    "type": "service_account",
    "project_id": "your-gcp-project-name",
    "private_key_id": "...",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
    "client_email": "sillytavern-vertex-ai@your-gcp-project-name.iam.gserviceaccount.com",
    "client_id": "...",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "..."
}
```

1. 使用简单的文本编辑器（例如 Windows 上的记事本、Mac 上的文本编辑或 VS Code）打开您刚刚下载的 .json 文件。
2. 选中文件中的所有文本（Ctrl+A 或 Cmd+A）。
3. 将文本复制到剪贴板（Ctrl+C 或 Cmd+C）。
4. 在 SillyTavern 中，进入“API 连接”页面，选择“聊天补全”作为 API 类型，然后从下拉菜单中选择“Google Vertex AI”。将身份验证方法切换为“服务账号”。
5. 将复制的全部内容粘贴到“服务账号 JSON 内容”文本框中。
6. 点击“验证 JSON”按钮，确保您正确复制了内容。
7. 最后，向下滚动并点击 API 设置页面底部的“连接”按钮。

现在您应该能够将 Google Vertex AI API 与 SillyTavern 一起使用了。

### 快速模式

快速模式是在 Google Cloud 上开始使用生成式 AI 的最快捷方式。它允许您无需设置服务账号即可使用 Gemini API，而是直接使用 API 密钥。

更多详细信息，请参阅官方文档：[Vertex AI 快速模式概述](https://cloud.google.com/vertex-ai/generative-ai/docs/start/express-mode/overview)。

#### 步骤 1：确保您的账号有资格使用快速模式

您必须拥有一个之前未用于创建 Google Cloud 项目的 Google 账号。
如果您有现有的 Google Cloud 项目（包括免费试用项目），您可以为此目的创建一个新项目。

#### 步骤 2：激活 Vertex AI 快速模式

1. 访问以下网页：[Vertex AI Studio](https://cloud.google.com/generative-ai-studio)。
2. 点击“免费试用”。
3. 接受条款和条件，并使用您的 Google 账号登录。
4. 选择您的国家/地区，点击“同意并开始免费试用”。等待设置完成。

#### 步骤 3：创建 API 密钥

1. 确认您的 Google Cloud 控制台正在以快速模式运行。您应该在页面左上角看到一个横幅。
2. 点击左侧边栏中的“API 密钥”链接。
3. 点击“创建 API 密钥”按钮。
4. 将生成一个新的 API 密钥。将此密钥复制到剪贴板。

#### 步骤 4：将 API 密钥填入 SillyTavern

1. 在 SillyTavern 中，进入“API 连接”页面。
2. 选择“聊天补全”作为 API 类型。
3. 从下拉菜单中选择“Google Vertex AI”。
4. 将身份验证方法切换为“快速模式（API 密钥）”。
5. 将您之前复制的 API 密钥粘贴到“API 密钥”文本框中。
6. 点击“连接”按钮保存密钥。

现在您应该能够在快速模式下将 Google Vertex AI API 与 SillyTavern 一起使用了。