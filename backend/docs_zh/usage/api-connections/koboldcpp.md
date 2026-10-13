
# KoboldCpp

KoboldCpp 是一个用于 GGML 和 GGUF 模型的独立 API。

Nyx 制作的这个 [VRAM 计算器](https://huggingface.co/spaces/NyxKrage/LLM-Model-VRAM-Calculator) 可以告诉你模型大约需要多少 RAM/VRAM。

## Nvidia GPU 快速入门

本指南假设你使用的是 Windows 系统。

* 下载最新版本：<https://github.com/LostRuins/koboldcpp/releases>
* 启动 KoboldCpp。你可能会看到 Microsoft Defender 弹出提示，点击“仍然运行”。
* 从版本 1.58 开始，KoboldCpp 的界面如下：

![KoboldCpp 1.58](/static/koboldcpp.png)

* 在 `Quick Launch`（快速启动）标签页下，选择模型和你偏好的 `Context Size`（上下文大小）。
* 选择 `Use CuBLAS`（使用 CuBLAS），并确保 `GPU ID` 旁边的黄色文字与你的 GPU 匹配。
* 即使你的 VRAM 较低，也不要勾选 `Low VRAM`（低 VRAM）。
* 除非你使用的是 Nvidia 10 系列或更老的 GPU，否则请取消勾选 `Use QuantMatMul (mmq)`（使用量化矩阵乘法）。
* 加载模型后，`GPU Layers`（GPU 层数）应已自动填入。暂时保持不动。
* 在 `Hardware`（硬件）标签页下，勾选 `High Priority`（高优先级）。
* 点击 `Save`（保存），这样你就不必每次启动时都重新配置 KoboldCpp。
* 点击 `Launch`（启动），等待模型加载。

你应该会看到类似下面的内容：

```txt
Load Model OK: True
Embedded Kobold Lite loaded.
Starting Kobold API on port 5001 at http://localhost:5001/api/
Starting OpenAI Compatible API on port 5001 at http://localhost:5001/v1/
======
Please connect to custom endpoint at http://localhost:5001
```

现在你可以在 SillyTavern 中连接到 KoboldCpp，API URL 使用 `http://localhost:5001`，然后开始聊天。

**恭喜！你已完成！**

某种程度上算是完成了。

### GPU 层数

KoboldCpp 已经在运行，但你可以通过确保尽可能多的层数被卸载到 GPU 上来提升性能。你会在终端中看到类似下面的内容：

```txt
llm_load_tensors: offloading 9 repeating layers to GPU
llm_load_tensors: offloaded 9/33 layers to GPU
llm_load_tensors:        CPU buffer size = 25215.88 MiB
llm_load_tensors:      CUDA0 buffer size =  7043.34 MiB
....................................................................................................
llama_kv_cache_init:  CUDA_Host KV buffer size =  1479.19 MiB
llama_kv_cache_init:      CUDA0 KV buffer size =   578.81 MiB
```

不要被数字吓到；这部分比看起来简单。`CPU buffer size` 指的是系统 RAM 的使用量，忽略它。`CUDA0 buffer size` 指的是 GPU VRAM 的使用量。`CUDA_Host KV buffer size` 和 `CUDA0 KV buffer size` 指的是分配给模型上下文的 GPU VRAM 大小。在这个例子中，KoboldCpp 使用了大约 9 GB 的 VRAM。

我有 12 GB 的 VRAM，其中只有 2 GB 用于上下文，所以我还剩大约 10 GB 的 VRAM 来加载模型。由于 9 层使用了大约 7 GB 的 VRAM，且 `7000 / 9 = 777.77`，我们可以假设每层大约使用 `777.77 MiB` 的 VRAM。`10,000 MiB / 777.77 = 12.8`，所以我向下取整，从此以后用这个模型加载 12 层。

现在根据你的系统（模型、上下文大小和 VRAM）自己计算，然后重启 KoboldCpp：

* 如果你够聪明，之前已经点击了 `Save`，现在可以用 `Load` 加载之前的配置。否则，选择之前相同的设置。
* 将 `GPU Layers` 改为你新计算的、优化 VRAM 的数值（我的例子中是 12 层）。
* 点击 `Save` 保存更新后的配置。

你现在应该会看到类似下面的内容：

```txt
llm_load_tensors: offloading 12 repeating layers to GPU
llm_load_tensors: offloaded 12/33 layers to GPU
llm_load_tensors:        CPU buffer size = 25215.88 MiB
llm_load_tensors:      CUDA0 buffer size =  9391.12 MiB
....................................................................................................
llama_kv_cache_init:  CUDA_Host KV buffer size =  1286.25 MiB
llama_kv_cache_init:      CUDA0 KV buffer size =   771.75 MiB
```

KoboldCpp 使用了 12 GB VRAM 中的大约 11.5 GB。这应该比 KoboldCpp 自动生成的设置性能好很多。

**恭喜！你（真正）完成了！**

关于 KoboldCpp 设置的更深入介绍，请查看 Kalomaze 的 [Simple Llama + SillyTavern Setup Guide](https://rentry.org/llama_v2_sillytavern)。