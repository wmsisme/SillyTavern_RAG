
# TabbyAPI
一个基于 FastAPI 的应用程序，允许使用 Exllamav2 后端通过 LLM 生成文本，支持 Exl2、GPTQ 和 FP16 模型。

* [GitHub](https://github.com/theroyallab/tabbyAPI)

### 快速开始
1. 按照 TabbyAPI 官方 GitHub 上的[安装说明](https://github.com/theroyallab/tabbyAPI/wiki/01.-Getting-Started)进行操作。
2. [创建您的 config.yml](https://github.com/theroyallab/tabbyAPI/wiki/02.-Server-options)，设置模型路径、默认模型、序列长度等。如果愿意，可以忽略大部分（甚至全部）这些设置。
3. 启动 TabbyAPI。如果启动成功，您应该会看到类似这样的信息：

    ![TabbyAPI 终端](/static/tabby-terminal.png)

4. 在 SillyTavern 的文本补全 API 下，选择 TabbyAPI。
5. 将 TabbyAPI 终端中的 API 密钥复制到 `Tabby API 密钥` 中，并确保 `API URL` 正确（默认应为 `http://127.0.0.1:5000`）。

如果一切操作正确，您应该在 SillyTavern 中看到类似这样的界面：

![TabbyAPI SillyTavern](/static/tabby-config.png)

现在您可以使用 TabbyAPI 进行聊天了！

### TabbyAPI 加载器
TabbyAPI 的开发者创建了一个官方扩展，用于直接从 SillyTavern 加载/卸载模型。安装很简单：
1. 在 SillyTavern 中，点击扩展选项卡，然后导航到下载扩展与资源。
2. 将 `https://raw.githubusercontent.com/theroyallab/ST-repo/main/index.json` 复制到资源 URL 中，然后点击右侧的插头按钮。
3. 您应该会看到类似这样的界面。点击 Tabby 加载器旁边的下载按钮。

    ![Tabby 加载器](/static/tabby-assets.png)

4. 如果安装成功，您应该在屏幕顶部看到一条绿色的弹出消息。在扩展选项卡下，导航到 TabbyAPI 加载器，并将 TabbyAPI 终端中的管理密钥复制到管理密钥中。
5. 点击模型选择旁边的刷新按钮。当您点击其下方的文本框时，应该会看到模型目录中的所有模型。

![Tabby 加载器扩展](/static/tabby-loader.png)

现在您可以直接从 SillyTavern 加载和卸载模型了！

### 支持
仍然需要帮助？访问 [TabbyAPI GitHub](https://github.com/theroyallab/tabbyAPI) 获取开发者官方 Discord 服务器的链接，并[阅读维基](https://github.com/theroyallab/tabbyAPI/wiki/1.-Getting-Started)。