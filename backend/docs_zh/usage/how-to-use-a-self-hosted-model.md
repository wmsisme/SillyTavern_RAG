
# 自托管 AI 模型

> **⚠️ Warning**
>
> 本指南基于作者的个人经验与知识，并非绝对真理。所有陈述仅供参考。如有任何修正或建议，请通过 Discord 联系我们，或向 [SillyTavern 文档仓库](https://github.com/SillyTavern/SillyTavern-Docs) 提交 PR。


## 简介

本指南旨在帮助你配置 SillyTavern，使其与运行在电脑上的本地 AI（从现在开始我们将使用恰当术语，称之为 LLM）协同工作。在向他人提出技术支持问题之前，请先阅读本文。

### 什么是最好的大语言模型？

这个问题无法回答，因为没有标准化的“最佳”尺度。社区在 Reddit 和 Discord 上有足够的资源和讨论，足以形成关于首选/首选模型的一些看法。你的体验可能有所不同。

### 什么是最好的配置？

如果存在一种最佳或无需思考的配置，那还需要配置吗？最好的配置就是适合你的配置。这是一个反复试错的过程。

## 硬件要求与定位

这是一个复杂的话题，所以我将只讲要点并进行概括。

- 互联网上有成千上万的免费 LLM 可供下载，类似于 Stable Diffusion 有大量模型可用于生成图像。
- 运行未经修改的 LLM 需要一个拥有巨大显存（GPU 内存）的怪兽级 GPU。比你拥有的要多得多。
- 可以通过使用量化技术（如 GPTQ 或 AWQ）压缩模型来降低显存需求。这会使模型能力略有下降，但大大降低了运行所需的显存。突然间，像 3080 这样的游戏级 GPU 也能运行 13B 模型了。虽然不如未量化模型那么好，但仍然不错。
- 情况变得更好：还有一种称为 GGUF（原 GGML）的模型格式和量化方式，已成为没有怪兽级 GPU 的普通人的首选格式。这允许你完全不需要 GPU 就能使用 LLM。它只使用 CPU 和内存。这比使用 GPTQ/AWQ 在 GPU 上运行 LLM 慢得多（可能慢 15 倍），尤其是在提示处理阶段，但模型的能力同样出色。GGUF 的创建者随后通过添加一个配置选项进一步优化了 GGUF，该选项允许拥有游戏级 GPU 的用户将模型的部分层卸载到 GPU，从而实现部分模型以 GPU 速度运行（注意，这不会降低内存需求，只会提高生成速度）。
- 模型有不同的尺寸，以其训练时的参数数量命名。你会看到像 7B、13B、30B、70B 这样的名称。你可以将它们视为模型的“大脑尺寸”。同一模型家族中的 13B 模型会比 7B 模型能力更强：它们基于相同的数据训练，但更大的大脑能更好地保留知识并更连贯地思考。更大的模型也需要更多的显存/内存。
- 量化有多个等级（8 位、5 位、4 位等）。等级越低，模型退化越严重，但硬件要求也越低。因此，即使在较差的硬件上，你也可能运行所需模型的 4 位版本。甚至还有 3 位和 2 位量化，但到了这个地步，你已经是在强弩之末了。还有进一步的量化子类型，如 k_s、k_m、k_l 等。k_m 优于 k_s，但需要更多资源。
- 上下文大小（在不丢失部分内容的情况下，对话可以持续多长）也会影响显存/内存需求。幸运的是，这是一个可配置的设置，允许你使用较小的上下文来降低显存/内存需求。（注意：基于 Llama2 的模型的上下文大小为 4k。Mistral 声称是 8k，但实际上也是 4k。）
- 在 2023 年的某个时候，NVIDIA 更改了他们的 GPU 驱动程序，因此当你的显存不足时，任务不会崩溃，而是开始使用常规内存作为后备。这会降低 LLM 的写作速度，但模型仍然能工作并提供相同质量的输出。幸运的是，这种行为[可以禁用](https://nvidia.custhelp.com/app/answers/detail/a_id/5490)。

综上所述，硬件要求和性能完全取决于模型家族、模型类型、模型大小、量化方法等因素。

#### 模型大小计算器
你可以使用 [Nyx's Model Size Calculator](https://huggingface.co/spaces/NyxKrage/LLM-Model-VRAM-Calculator) 来确定你需要多少内存/显存。

记住，你想要运行的是能装进你内存的最大、量化程度最低的模型，即不会导致[磁盘交换](https://serverfault.com/a/48487)。

## 下载 LLM

要开始，你需要下载一个 LLM。查找和下载 LLM 最常用的地方是 HuggingFace。那里有成千上万的模型可用。寻找 GGUF 模型的一个好方法是查看 bartowski 的个人页面：<https://huggingface.co/bartowski>。如果你不想要 GGUF，他会链接到原始模型页面，在那里你可以找到同一模型的其他格式。

在某个模型的页面中，你会看到一大堆文件。

- 你不需要全部下载！对于 GGUF，你只需要 .gguf 模型文件（通常 4-11GB）。如果你看到多个大文件，它们通常都是同一模型的不同量化版本，你只需选择一个。
- 对于 .safetensors 文件（可能是 GPTQ、AWQ、HF 量化或未量化），如果文件名中带有数字序列，如 model-00001-of-00003.safetensors，那么你需要所有这 3 个 .safetensors 文件以及仓库中的所有其他文件（分词器、配置文件等）才能获得完整模型。
- 截至 2024 年 1 月，Mixtral MOE 8x7B 被广泛认为是本地 LLM 的尖端模型。如果你有 32GB 内存来运行它，绝对值得一试。如果你内存少于 32GB，请使用 Kunoichi-DPO-v2-7B，尽管它尺寸不大，但表现非常出色。

### 下载 Kunoichi-DPO-v2-7B 的步骤

本指南的其余部分将使用 Kunoichi-DPO-v2-7B 模型。这是一个基于 Mistral 7B 的优秀模型，仅需 7GB 内存，性能远超其规模。注意：Kunoichi 使用 Alpaca 提示格式。

- 前往 <https://huggingface.co/brittlewis12/Kunoichi-DPO-v2-7B-GGUF>
- 点击“Files and versions”。你会看到几个文件的列表。这些都是同一个模型，但提供了不同的量化选项。点击文件 'kunoichi-dpo-v2-7b.Q6_K.gguf'，这会给我们提供一个 6 位量化。
- 点击“download”按钮。下载应该会开始。

### 如何识别模型类型

像 TheBloke 这样的好上传者会给出描述性的名称。但如果他们没有：

- 文件名以 .gguf 结尾：GGUF CPU 模型（显然）
- 文件名以 .safetensors 结尾：可能是未量化、HF 量化、GPTQ 或 AWQ
- 文件名为 pytorch-***.bin：同上，但这是较旧的模型文件格式，允许模型在加载时执行任意 Python 脚本，被认为不安全。如果你信任模型创建者或别无选择，仍可使用它，但如果有选项，请选择 .safetensors。
- 存在 config.json？查看它是否有 quant_method。
- q4 表示 4 位量化，q5 表示 5 位量化，依此类推。
- 看到像 -16k 这样的数字？那是增加的上下文大小（即对话能持续多长而模型不会忘记开头）！注意，更大的上下文大小需要更多显存。

## 安装 LLM 服务器：Oobabooga 或 KoboldAI

现在 LLM 已经在你的电脑上，我们需要下载一个工具，作为 SillyTavern 和模型之间的中间人：它将加载模型，并将其功能暴露为本地 HTTP Web API，SillyTavern 可以与之通信，就像 SillyTavern 与 OpenAI GPT 或 Claude 等付费 Web 服务通信一样。你使用的工具应该是 KoboldAI 或 Oobabooga（或其他兼容工具）。

本指南涵盖了这两种选项，你只需要其中一个。

> **⚠️ Warning**
>
> 如果你在 Docker 上托管 SillyTavern，请使用 **http://host.docker.internal:\<port\>** 而不是 **http://127.0.0.1:\<port\>**。这是因为 SillyTavern 从运行在 Docker 容器中的服务器连接到 API 端点。Docker 的网络栈与主机的网络栈是分离的，因此回环接口不共享。


### 下载并使用 KoboldCpp（无需安装，GGUF 模型）

1. 访问 https://koboldai.org/cpp ，你会看到最新版本以及各种可供下载的文件。
   在撰写本文时，他们列出的最新 CUDA 版本是 cu12，最适合现代 NVIDIA GPU；如果你有较旧的 GPU 或其他品牌，可以使用常规的 koboldcpp.exe。如果你有旧 CPU，KoboldCpp 在尝试加载模型时可能会崩溃，在这种情况下，请尝试 _oldcpu 版本看是否能解决问题。
2. KoboldCpp 无需安装，启动 KoboldCpp 后，你将能立即使用“Model”字段旁边的“Browse”按钮选择你的 GGUF 模型（例如上面链接的那个）。
3. 默认情况下，KoboldCpp 最大上下文为 4K，即使你在 SillyTavern 中设置得更高也是如此。如果你希望以更高上下文运行模型，请确保在此屏幕上的启动模型之前调整上下文滑块。请记住，更大的上下文大小意味着更高的（视频）内存需求；如果设置得太高或加载的模型对于你的系统来说太大，KoboldCpp 将自动开始使用 CPU 处理无法放入 GPU 的层，这将会慢得多。
4. 点击“Launch”，如果一切顺利，将打开一个带有 KoboldAI Lite 的新网页，你可以在那里测试一切是否正常。
5. 打开 SillyTavern，点击“API Connections”（顶部栏第二个按钮）。
6. 将 API 设置为“Text Completion”，API 类型设置为“KoboldCpp”。
7. 将服务器 URL 设置为 <http://127.0.0.1:5001/> 或 KoboldCpp 给你的链接（如果它不在同一系统上运行）。你可以激活 KoboldCpp 的远程隧道模式以获得一个可从任何地方访问的链接。
8. 点击“Connect”。它应该成功连接并检测到模型为 kunoichi-dpo-v2-7b.Q6_K.gguf。
9. 与角色聊天以测试其工作。

### 优化 KoboldCpp 速度的技巧
1. Flash Attention 有助于减少内存需求，根据系统不同可能更快或更慢，并允许你在 GPU 上容纳比默认更多的层。
2. KoboldCpp 在猜测层数时会预留一些空间给其他软件以防止问题。如果你打开的程序很少并且无法将模型完全放入 GPU，你可能可以添加额外的几层。
3. 如果模型在给定上下文大小下占用过多内存，你可以通过对 KV 进行量化来减少内存。这会降低输出质量，但有助于将更多层放在 GPU 上。为此，前往 KoboldCpp 中的“Tokens”选项卡，禁用“Context Shifting”并启用“Flash Attention”。这将解锁“Quantized KV Cache”滑块，数值越低意味着模型使用的内存/智能越少。
4. 在较慢的系统上运行 KoboldCpp，提示处理时间很长？当你避免使用 Lorebooks、随机化或其他动态改变输入的功能时，Context Shifting 效果最好。保持 Context Shifting 启用，KoboldCpp 将帮助你避免长时间重新处理。

### 安装 Oobabooga

> **📝 Note**
>
> 根据你安装 Oobabooga 的方式，文件路径可能略有不同；例如，如果通过 git clone 安装，路径为 `/text-generation-webui/user_data`；如果使用 .zip 方法，路径为 `/text-generation-webui-main/user_data`。


这里有一个更正确/防呆的安装过程：

1. git clone <https://github.com/oobabooga/text-generation-webui>（或在浏览器中下载他们的仓库为 .zip，然后解压）
2. 运行 `start_windows.bat` 或适用于你操作系统的脚本。
3. 当提示时，选择你的 GPU 类型。即使你打算使用 GGUF/CPU，如果你的 GPU 在列表中，现在也请选择它，因为它将为你提供以后使用 GPU 分片的速度优化选项（无需从头重新安装）。如果你没有游戏级独立 GPU（NVIDIA、AMD），选择“None”。
4. 等待安装完成。
5. 将 kunoichi-dpo-v2-7b.Q6_K.gguf 放入 `text-generation-webui/user_data/models`。
6. 打开 `text-generation-webui/user_data/CMD_FLAGS.txt`，删除里面的所有内容并写入：`--api`
7. 重启 Oobabooga。
8. 访问 <http://127.0.0.1:5000/docs>。是否加载了一个 FastAPI 页面？如果没有，说明你在某处出错了。

### 在 Oobabooga 中加载我们的模型

1. 在浏览器中打开 <http://127.0.0.1:7860/>
2. 点击“Model”选项卡。
3. 在下拉菜单中，选择我们的 Kunoichi DPO v2 模型。它应该已经自动选择了 llama.cpp 加载器。
4. （可选）我们之前多次提到“GPU offload”：即此页面上的 n-gpu-layers 设置。如果你想使用它，在加载模型之前设置一个值。作为基本参考，将其设置为 30 对于 13B 及更小的模型占用略低于 6GB 显存（因模型架构和大小而异）。
5. 点击“Load”。

### 配置 SillyTavern 与 Oobabooga 通信

1. 点击“API Connections”（顶部栏第二个按钮）。
2. 将 API 设置为“Text Completion”。
3. 将 API 类型设置为“Default (Oobabooga)”。
4. 将服务器 URL 设置为 <http://127.0.0.1:5000/>
5. 点击“Connect”。它应该成功连接并检测到模型为 kunoichi-dpo-v2-7b.Q6_K.gguf。
6. 与角色聊天以测试其工作。

## 结论

恭喜，你现在应该拥有一个可工作的本地 LLM 了。