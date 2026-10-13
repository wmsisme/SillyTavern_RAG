
# 基于检索的语音转换 (RVC)

本指南将引导您使用RVC，这是一种允许将语音特征从一个音频片段转移到另一个音频片段的技术，从而使语音能够以不同的语调和风格说话。

您是否曾喜爱那些著名的“总统玩X”视频？它们就是使用RVC制作的。借助RVC扩展，您可以让您的SillyTavern角色以任何您想要的语音说话，无论是动漫、电影，甚至是您自己独特的嗓音。

RVC不是TTS：它更像是语音到语音。它接收一个音频片段作为输入。在后台，RVC所做的是与SillyTavern的TTS扩展协同工作：它等待TTS生成一个音频文件（无论是否使用RVC，TTS都会生成该文件），然后RVC会进行第二次处理，将TTS音频文件转换为您RVC配置中克隆的声音。

## RVC 设置

SillyTavern的RVC支持多个执行音频转换的API来源：

* [rvc-python](https://github.com/daswer123/rvc-python)
* [SillyTavern Extras](https://github.com/SillyTavern/SillyTavern-Extras) (已弃用)

### 通用前提条件

在开始之前，请确保您已满足以下前提条件。

#### ffmpeg

确保您的PATH环境变量中包含`ffmpeg`可执行文件。此工具用于转换传入的音频。

**Windows**：

* 使用SillyTavern Launcher脚本中的工具箱自动安装ffmpeg：<https://github.com/SillyTavern/SillyTavern-Launcher>
* 或者在此处下载构建版本：<https://www.gyan.dev/ffmpeg/builds/>
* 如何修改PATH变量：<https://www.architectryan.com/2018/03/17/add-to-the-path-on-windows-10/>
* 要测试操作是否正确，请打开命令提示符并运行```ffmpeg```。它应打印ffmpeg版本和信息。

**Linux**：

使用您的包管理器安装ffmpeg。

```shell
# Debian/Ubuntu
sudo apt install ffmpeg
# Arch Linux
sudo pacman -S ffmpeg
# Fedora
sudo dnf install ffmpeg
```

**macOS**：

使用[Homebrew](https://brew.sh/)安装ffmpeg：

```shell
brew install ffmpeg
```

#### 确保TTS已启用并能正常工作

RVC依赖于TTS；您需要启用一个TTS扩展。在您尝试将RVC加入组合之前，您的TTS必须已经正常工作并为您的聊天内容配音！

请注意：

* 系统TTS引擎根本不支持语音转换。
* 流式TTS会等待音频流结束后再进行转换。

#### 安装扩展

从扩展面板（堆叠块图标）中的“下载扩展和资源”菜单安装“RVC”扩展。

#### 在SillyTavern中启用RVC*

在SillyTavern中，导航至**扩展** > **RVC**并启用它。

#### 选择来源

在扩展设置中，选择要使用的RVC来源。然后继续阅读该来源特定的安装说明。

### rvc-python 设置

#### 1. 安装包

按照GitHub页面上的安装说明进行操作：[rvc-python Installation](https://github.com/daswer123/rvc-python?tab=readme-ov-file#installation)。如果您有Nvidia GPU，建议遵循CUDA安装说明。

如果您在Windows上安装时遇到问题（例如，构建fairseq步骤失败），请确保您的PC上安装了以下软件：

* [Windows 10 SDK](https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/)
* [Visual Studio Build Tools 2022](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)

#### 2. 准备模型

创建一个用于存储RVC模型的目录。默认情况下，它名为`rvc_models`，并在启动服务器时从当前目录中获取。每个模型都是一个子文件夹（其名称将在UI中可见），应包含`.pth`（必需）和`.index`（可选）文件。

了解更多：[rvc-python Model Management](https://github.com/daswer123/rvc-python?tab=readme-ov-file#model-management)

#### 3. 启动API服务器

通过运行以下命令启动API服务器：

```shell
python -m rvc_python api -p 5050 -l -md models_path
```

**参数：**

* `5050` - 设置服务器的监听端口。如果您想在不同的端口上托管，请更改。
* `models_path` - 设置模型的路径。如果要使用默认的`rvc_models`目录，请移除。
* `-l` - 设置服务器在所有网络接口上监听。移除则仅在本地主机上监听。

#### 4. 连接到服务器

* 在RVC扩展设置中，设置适当的**rvc-python API URL**。默认情况下，它将为`http://localhost:5050`。
* 如果您已安装支持CUDA加速的rvc-python，请勾选**使用CUDA**复选框。
* 按“刷新”以加载可用语音列表。

#### 5. 配置语音映射

**语音映射定义了每个角色或用户角色的语音转换设置。**

* 要设置语音映射，请从“角色”下拉列表中选择您的角色或角色名称，然后选择一个RVC“语音”，再单击“应用”。
* 可选地，您还可以配置其他相关设置，如音高修正或过滤。
* 如果操作正确，语音映射调试区域将显示类似“Betty:MyVoice(rmvpe)”的内容。

### SillyTavern Extras 设置

#### 1. 准备RVC模型文件

* 在文件浏览器中，导航至：`\SillyTavern-extras\data\models\rvc`。
* 创建一个子文件夹，例如“Betty”，并将`.pth`和`.index`文件放入其中。（提示：您可以从https://voice-models.com下载语音文件，确保语音名称表明它是RMVPE。）

#### 2. 安装依赖项

使用以下命令安装必要的依赖项：

```shell
pip install -r requirements-rvc.txt`
```

#### 3. 启用RVC运行SillyTavern-extras

启动启用了RVC模块的SillyTavern-extras。此示例调用假设您使用了随SillyTavern-extras预装的Edge TTS：

```shell
python server.py --enable-modules=rvc,edge-tts
```

可选地，如果您拥有合适的GPU，您可能希望通过在启动命令中添加```--cuda```来在GPU上运行RVC。根据快速测试，叙述50个令牌（约36个单词）时VRAM使用量为3.4GB，200个令牌（约150个单词）时为7.6GB。

#### 4. 设置语音映射

为RVC创建语音映射。将您的角色设置为所需的SillyTavern角色名称，将语音设置为您在第1步创建的RVC文件夹，然后单击“应用”。如果操作正确，语音映射将显示类似“Betty:MyVoice(rmvpe)”的内容。

#### 5. 选择音高提取方法

* 选择“rmvpe”作为音高提取方法。
* 如果“rmvpe”遇到问题，请尝试其他方法（例如，“harvest”或“torchcrepe”）。

#### 6. （可选）配置RVC将生成结果保存到文件

如果出于测试或故障排除目的，您希望保存生成的RVC音频，请在启动命令中添加```--rvc-save-file```。这将把最后一次生成的结果保存在`SillyTavern-extras/data/tmp/rvc_output.wav`下：

```shell
python server.py --enable-modules=rvc,edge-tts --rvc-save-file
```

### 基于表情的动态语音

#### 1. 配置RVC模型

在您的RVC模型文件夹中，为每种分类的表情（例如，愤怒、恐惧、喜悦、爱、悲伤、惊讶）分别准备单独的`.pth`和`.index`文件。

#### 2. 启用模块

同时启用RVC和classify模块：

```shell
python server.py --enable-modules=rvc,classify
```

#### 3. 使用RVC模块

其余设置与单独使用RVC模块类似（如上所述）。

## 训练您自己的RVC模型

### 使用Deffcolony的RVC Easy Menu（仅限Windows）

自动安装并启动Mangio-RVC：https://github.com/deffcolony/rvc-easy-menu

#### 1. 克隆仓库

将仓库克隆到您想要的位置：

```shell
git clone https://github.com/deffcolony/rvc-easy-menu.git
```

#### 2. 启动RVC-Launcher.bat

* 打开`RVC-Launcher.bat`文件。
* 选择选项1安装RVC。

#### 3. 完成安装

按提示安装所需的包和依赖项。

#### 4. 打开WebUI进行语音训练

安装完成后，选择选项2打开WebUI进行语音训练。

### Mangio-RVC：训练语音模型

***数据集准备***：

**1. 准备音频**：

* 将您想要训练的音频放入`datasets`文件夹。
* 确保音频没有背景噪音——只需要原始语音。
* 较长的音频能带来更好的输出质量。

***WebUI训练***：

**1. 访问训练标签页**：

* 在WebUI中点击训练标签页。

**2. 配置实验**：

* 输入实验名称（例如，`my-epic-voice-model`）。
* 将版本设置为v2。

**3. 处理数据和提取特征**：

* 点击“处理数据”和“特征提取”。
* 将“保存频率”设置为50。

**4. 训练参数**：

* 将“总训练轮数”设置为300。
* 点击“训练特征索引”和“训练模型”。