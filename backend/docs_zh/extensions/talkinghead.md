
# talkinghead

> **⚠️ Warning**
>
> **SILLYTAVERN 1.12.13 版本已移除了对 TALKINGHEAD 的支持。此页面仅用于历史存档。**


### 这是什么？

针对 AITuber 的 Talking Head Anime 3 演示实现。具有以下功能：

- 从单张静态图像生成随机的类似 Live 2D 的动态动作。
- 对任何 TTS 输出的音频进行唇形同步。

该扩展包含“从单张图像生成会说话的（？）动漫角色 3：现在身体也可以动”项目的原始演示程序。顾名思义，该项目允许您对角色的动作进行动画处理，且只需一张角色图像即可。包含两个演示程序：

manual_poser 让您通过图形用户界面操控角色的面部表情、头部旋转、身体旋转以及呼吸引起的胸部扩张，并可将这些状态保存为默认表情（如高兴、悲伤、喜悦等）。
ifacialmocap_puppeteer 让您将面部动作迁移到动漫角色上。

### 硬件要求

您可以使用 CPU 或 GPU 模式（默认使用 CPU）。但在 CPU 模式下预计只有约 1 FPS，而在 RTX3060 的 GPU 模式下则可达到约 9-10 FPS。

ifacialmocap_puppeteer 需要一个能够从视频流计算混合形状参数的 iOS 设备。也就是说，设备必须能运行 iOS 11.0 或更高版本，并且必须配备 TrueDepth 前置摄像头。（更多信息请参见此页面。）换言之，如果您拥有 iPhone X 或更高型号，即可满足要求。

### 使用方法

您必须使用以下模块启动 extras 才能让 talkinghead 正常工作：`classify` 和 `talkinghead`！
classify 用于处理 talkinghead.png 文件。此外，您还可以使用 `--talkinghead-gpu` 将混合模型加载到 GPU 内存中，从而使动画速度提升 10 倍。强烈建议使用 GPU 加速！默认情况下，程序启动后会加载默认图像 SillyTavern-extras\talkinghead\tha3\images\lambda_00.png。您可以通过访问 http://localhost:5100/api/talkinghead/result_feed 或 `YOUR EXT URL:PORT/api/talkinghead/result_feed` 来验证其是否正常工作。

- 服务器启动后，进入 Extension API 标签页并连接。然后只需选择要加载的角色卡片。（启动 server.py 时使用 `--enable-modules=classify,talkinghead --talkinghead-gpu`）

- 现在选择角色表情，如果您勾选了 talkinghead 类型的图像复选框，脚本会将该角色的当前表情替换为 `YOUR EXT URL:PORT/api/talkinghead/result_feed` 的结果。取消勾选复选框应恢复为原始表情，但有时您需要向聊天发送一条新消息来“重新加载”图像。

- 如果角色目录中没有 talkinghead.png 文件，则会显示默认图像或最后一张包含 talkinghead.png 文件的角色卡片。更换角色卡片时会改变动画源图像。

- 现在打开角色表情，向下滚动到 talkinghead 图像上传区域，上传一张符合下方“输入图像约束”部分要求的图像文件。

- 然后勾选再取消勾选 talkinghead 复选框以重新加载角色。如果图像看起来很奇怪，很可能是因为它没有透明度（没有 Alpha 通道）。否则，请按照下面的说明和模板操作。

### 输入图像约束

为了使系统正常工作，输入图像必须满足以下约束条件：

- 分辨率应为 512 x 512。（如果程序接收到其他尺寸的输入图像，它会将其缩放至该分辨率并同样以该分辨率输出。）
- 必须包含 Alpha 通道。
- 只能包含一个人形角色。
- 角色应直立站立且面朝前方。
- 角色的手应位于头部下方并远离头部。
- 角色头部应大致位于图像上半部分中央的 128 x 128 框内。
- 所有不属于角色的像素（即背景像素）的 Alpha 通道必须为 0。

![输入约束](/static/input_spec.png)

### 高级部分

### Python 环境

除了基础功能 (app.py) 外，manual_poser 和 ifacialmocap_puppeteer 都可以作为桌面应用程序运行。要运行它们，您需要搭建一个用于运行 Python 语言编写的程序的环境。该环境需要包含以下软件包：

* Python >= 3.8
* PyTorch >= 1.11.0（支持 CUDA）
* SciPY >= 1.7.3
* wxPython >= 4.1.1
* Matplotlib >= 3.5.1

一种方法是通过安装 Anaconda，然后在 shell 中运行以下命令：

> conda create -n talking-head-anime-3-demo python=3.8
> conda activate talking-head-anime-3-demo
> conda install pytorch torchvision torchaudio cudatoolkit=11.3 -c pytorch
> conda install scipy
> pip install wxpython
> conda install matplotlib

### 额外的混合模型

仅包含一个（最轻量级的）模型。如果您需要额外的混合模型，请从 https://www.dropbox.com/s/y7b8jl4n2euv8xe/talking-head-anime-3-models.zip?dl=0 下载模型文件，并将其解压到 SillyTavern-extras\talkinghead\tha3\models 文件夹中。最终，数据文件夹结构应如下所示：

+ tha3
  + models
    + separable_float
      - editor.pt
      - eyebrow_decomposer.pt
      - eyebrow_morphing_combiner.pt
      - face_morpher.pt
      - two_algo_face_body_rotator.pt
    + separable_half
      - editor.pt
          :
      - two_algo_face_body_rotator.pt
    + standard_float
      - editor.pt
          :
      - two_algo_face_body_rotator.pt
    + standard_half
      - editor.pt
          :
      - two_algo_face_body_rotator.pt

模型文件根据 Creative Commons Attribution 4.0 International License 分发，这意味着您可以将其用于商业目的。但创作者为 Pramook Khungurn。 Talking Head(?) Anime from a Single Image 3: Now the Body Too. <https://github.com/pkhungurn/talking-head-anime-3-demo>。

### 运行 manual_poser 桌面应用程序

打开一个 shell。将当前工作目录切换到仓库的根目录。然后运行：

> python tha3/app/manual_poser.py
请注意，在运行上述命令之前，您可能需要激活包含所需软件包的 Python 环境。

> conda activate extras
如果您尚未激活该环境的话。