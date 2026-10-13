
# AI Horde

## 免责声明

- AI Horde 是一个众包、分布式的 GPU 集群，完全由志愿者运营。
- 默认情况下，你的输入被匿名发送，Horde Worker 的运行者无法看到响应内容。
- 然而，由于它是一个开源程序，恶意 Worker 可能会修改代码以：
  - 记录你的活动（输入提示词、AI 响应）。
  - 产生不良或冒犯性的响应。

> **⚠️ Warning**
>
> 使用 Horde 时**切勿发送**任何个人信息，如姓名、电子邮件地址等。


勾选"仅限可信 Worker"复选框会限制可用 Worker 的选择范围，只保留那些已在 Horde 上运行一段时间且通常被认为可信的 Worker。但它们仍有可能看到提示词，例如通过使用未经审核的软件来运行。

为帮助缓解此问题，SillyTavern 内置了以下功能：

- 当聊天响应由 Horde Worker 生成时，SillyTavern 会记录该 Worker 的 ID 以及它们使用的模型。
- 将鼠标悬停在聊天条目上即可查看此信息（见下图）。
- 如果你认为自己收到了恶意响应，可以将此信息传递给 [AI Horde Discord](https://discord.gg/3DxrhksKzn) 上的 Horde 管理员，供其审查并对该 Worker 采取可能的纪律处分。

![Horde Worker 信息弹窗](/static/horde-worker.png)

## 设置

- SillyTavern 可以直接连接 Horde，无需额外设置。
- 在 ST API 面板的 API 下拉选择器中选择"AI Horde"。
- 在面板底部的模型选择器中选择一个或多个模型（角色的"AI 大脑"）。
- 选择一个角色并开始聊天。

![ST Kobold Horde API 连接面板](/static/horde-config.png)

> **⚠️ Warning**
>
> 默认情况下，你的 SillyTavern 实例连接到 Horde 的低优先级"访客账户"。
> 这意味着你可能需要等待很长时间才能得到回复。
> 为缩短等待时间，请参考以下提示。


## 提示

- [在 Horde 网站上注册一个账户](https://aihorde.net/register)，然后将你的 Horde 密钥填入 SillyTavern 的 Horde API 密钥框。
- [设置一个 Horde Worker](https://github.com/Haidra-Org/AI-Horde-Worker#readme)，让他人使用你的 GPU。
  - 让他人使用你的 GPU 可以赚取 [Kudos，一种仅限 Horde 的货币](https://github.com/Haidra-Org/AI-Horde/blob/main/FAQ.md#kudos)。
  - 你的账户拥有越多 Kudos，从其他 Horde Worker 获得聊天回复的速度就越快。
  - Kudos 还可用于在 [Stable Horde](https://stablehorde.net) 上生成 AI 图像。
    - SillyTavern 直接支持 Stable Horde 图像生成。
- 如果你的 GPU 性能不足以运行 AI，或者你没有计算机，你仍然可以[通过多种方式参与 Horde 社区以赚取 Kudos](https://github.com/Haidra-Org/AI-Horde/blob/main/FAQ.md#i-dont-have-a-powerful-gpu-how-can-i-get-kudos)。