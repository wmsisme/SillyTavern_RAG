
# 带语音克隆的 XTTS

大家好！你是否被那些展示 AI 文本转语音技术至今进展的 Reddit 帖子所震撼？

是否想为你那机器人的老婆/老公配上炫酷的新语音调制器？

别担心，这项惊人的突破性技术已经在你本地的 SillyTavern 中可用，你只需要一个简单的...

## 先决条件

1. 最新版本的 SillyTavern。
2. 已安装 [Miniconda](https://docs.conda.io/projects/miniconda/en/latest/miniconda-install.html)。
3. (Windows) 已安装 [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)。
4. 用于克隆语音的 WAV 文件（每个文件约 10 秒）。文件要求：PCM、单声道、22050Hz、16 位（通过 Audacity 转换）。
5. 创建一个包含 "speakers" 和 "output" 子文件夹的文件夹。将 WAV 文件放入 "speakers"。

示例文件夹结构：
```
C:\xtts
  - speakers
    - alice.wav
    - bob.wav
  - output
```

## 安装

[daswer123](https://github.com/daswer123) 制作了一个 API 服务器，它可以在你的电脑上运行 XTTSv2 模型，并连接到 SillyTavern 的 TTS 扩展。

它完全独立于 Extras API，并且会使用一个单独的环境。

**非常重要：**不要将以下要求安装到你的 Extras 环境或系统 Python 中。
这会破坏你的其他包，进行不必要的降级等。

以下说明使用 Miniconda 提供，但你也可以使用 venv 完成（此处不赘述）。
打开 Anaconda 命令提示符，逐行按照说明操作。

### 启动并运行服务器

1. 导航到你在先决条件步骤 4 中创建的文件夹。
    ```
    cd C:\xtts
    ```
2. 创建一个新的 conda 环境。从现在开始，我们称它为 `xtts`。
    ```
    conda create -n xtts
    ```
3. 激活新创建的环境。
    ```
    conda activate xtts
    ```
4. 将 Python 3.10 安装到你的环境中。出现提示时输入 "y" 确认。
    ```
    conda install python=3.10
    ```
5. 安装 XTTS 服务器及其依赖项。
    ```
    pip install xtts-api-server pydub
    ```
6. 安装 PyTorch。这可能需要一些时间。以下行安装带有 GPU 加速支持（CUDA）的 PyTorch。
如果你只想使用 CPU 推理，则去掉以 `--index-url` 开头的最后一部分。
    ```
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    ```
7. 在默认主机和端口上启动 XTTS 服务器：<http://localhost:8020>
    ```
    python -m xtts_api_server
    ```
8. 首次启动时，模型将被下载（约 2 GB）。
不要忘了仔细阅读 Coqui AI 的法律声明。哈哈，开玩笑的，只需再次输入 "y" 即可。

### 连接到 SillyTavern

1. 打开扩展面板，展开 TTS 菜单，在提供商列表中选择 "XTTSv2"。
2. 在 Language 下拉菜单中选择你的文本转语音语言（如果不是波兰语我会很伤心）。
3. 确认提供商端点指向 <http://localhost:8020>，并且 "Available voices" 显示你的语音样本列表。
4. 选择任意角色，并在语音样本和角色之间设置映射。
如果角色列表为空，多次点击 "Reload"。
5. 根据你的偏好配置其余的 TTS 设置。

### 现在一切就绪！

点击任何消息上下文操作菜单中的喇叭图标，即可听到从扬声器发出的美妙克隆语音。
生成需要一些时间，即使在高端 RTX GPU 上也无法实时生成。

### 流式传输？

可以使用最新版本的 XTTS 服务器进行 HTTP 流式传输，以便在生成可用时立即获得音频片段！

#### 这不适用于 RVC！

音频仍会生成（假设你使用的是最新版本的 RVC 扩展）并进行转换，但*不会进行流式传输*，因为 RVC 需要在开始转换之前拥有完整的音频文件。流式 RVC 仍在研究中...

#### 如何获得流式传输支持？

1. 将 SillyTavern 更新到最新版本。
2. 将 XTTS 服务器更新到最新版本。

    ```bash
    conda activate xtts
    pip install xtts-api-server --upgrade
    ```

3. 按常规方式启动并连接 XTTS 到 ST。
4. 在 SillyTavern 中启用 "Streaming" XTTS 扩展设置。

### 音频卡顿？

尝试增加 "chunk size" 设置。

参考：对于 200 的块大小，RTX 3090 可以产生不间断的音频，代价是稍微增加音频延迟。

### 如何重启 TTS 服务器？

只需执行安装说明中的步骤 1、3 和 7。

### Android？？？

不太可能，它无法运行需要 PyTorch 的应用程序，除非使用我们不提供支持的某种神秘黑魔法。你可以自行尝试，但遇到任何问题我们将不提供支持。

你最好的解决方案是在你的 PC 上通过本地网络托管 TTS API，只需不要忘记指定监听的主机和端口——请参阅 [README](https://github.com/daswer123/xtts-api-server/blob/main/README.md)。