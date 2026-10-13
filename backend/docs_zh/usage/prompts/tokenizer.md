
# 分词器

分词器是一种工具，用于将一段文本拆分为称为“令牌”的更小单元。这些令牌可以是单个单词，甚至是单词的一部分，例如前缀、后缀或标点符号。一个经验法则是，一个令牌通常对应 3~4 个字符的文本。

SillyTavern 提供了一个“最佳匹配”选项，该选项根据所使用的 API 提供商，尝试根据以下规则匹配分词器。

文本补全 API **（可覆盖）**：

1. NovelAI Clio：NerdStash 分词器。
2. NovelAI Kayra：NerdStash v2 分词器。
3. 文本补全：API 分词器（如果支持）或 Llama 分词器。
4. KoboldAI Classic / AI Horde：Llama 分词器。
5. KoboldCpp：模型 API 分词器。

如果结果不准确或希望进行试验，你可以为 SillyTavern 设置一个*覆盖分词器*，用于向 AI 后端发送请求时使用：

1. 无。每个令牌估算为约 3.3 个字符，向上取整为最接近的整数。**如果提示在高上下文长度下被截断，请尝试此选项。** 此方法被 KoboldAI Lite 使用。
2. Llama 分词器。用于 Llama 1/2 模型系列：Vicuna、Hermes、Airoboros 等。**如果你使用 Llama 1/2 模型，请选择此项。**
3. Llama 3 分词器。用于 Llama 3/3.1 模型。**如果你使用 Llama 3/3.1 模型，请选择此项。**
4. NerdStash 分词器。用于 NovelAI 的 Clio 模型。**如果你使用 Clio 模型，请选择此项。**
5. NerdStash v2 分词器。用于 NovelAI 的 Kayra 模型。**如果你使用 Kayra 模型，请选择此项。**
6. Mistral V1 分词器。用于较旧的 Mistral 模型系列及其微调版本。**如果你使用较旧的 Mistral 模型，请选择此项。**
7. Mistral Nemo 分词器。用于 Mistral Nemo 模型系列及其微调版本。**如果你使用 Mistral Nemo/Pixtral 模型，请选择此项。**
8. Yi 分词器。用于 Yi 模型。**如果你使用 Yi 模型，请选择此项。**
9. Gemma 分词器。用于 Gemini/Gemma 模型。**如果你使用 Gemma 模型，请选择此项。**
10. DeepSeek 分词器。用于 DeepSeek 模型（例如 R1）。**如果你使用 DeepSeek 模型，请选择此项。**
11. API 分词器。查询生成 API 以直接从模型获取令牌计数。已知支持的后端：Text Generation WebUI (ooba)、koboldcpp、TabbyAPI、Aphrodite API。**如果你使用支持的后端，请选择此项。**

聊天补全 API **（不可覆盖）**：

1. OpenAI：通过 [tiktoken](https://github.com/openai/tiktoken) 进行模型相关的分词。
2. Claude：通过 [WebTokenizers](https://github.com/mlc-ai/tokenizers-cpp) 进行模型相关的分词。
3. OpenRouter：为其相应模型使用 Llama、Mistral、Gemma、Yi 分词器。
4. Google AI Studio：Gemma 分词器。
5. AI21 API：Jamba 分词器（需要一次性下载）。
6. Cohere API：Command-R 或 Command-A 分词器（需要一次性下载）。
7. MistralAI API：Mistral V1 或 V3 分词器（需要一次性下载）。
8. DeepSeek API：DeepSeek 分词器（需要一次性下载）。
9. 回退分词器：GPT-3.5 turbo 分词器。

#### 额外分词器

这些分词器因其大小而未包含在默认安装中。首次使用时需要进行一次性下载。

1. Qwen2 分词器。
2. Command-R / Command-A 分词器。聊天补全中由 Cohere 源使用。
3. Mistral V3 (Nemo) 分词器。聊天补全中由 MistralAI 源使用（Nemo 和 Pixtral 模型）。
4. DeepSeek (deepseek-chat) 分词器。聊天补全中由 DeepSeek 源使用。

如果你不想使用网络下载，可以在 config.yaml 中找到退出选项：`enableDownloadableTokenizers`。设置为 `false` 以禁用下载。

你也可以从 [SillyTavern-Tokenizers](https://github.com/SillyTavern/SillyTavern-Tokenizers) 仓库手动下载分词器。下载 JSON 文件并将其放入数据根目录的 `_cache` 子目录中，默认路径为 `./data/_cache`。如果 `_cache` 目录不存在，请创建它。之后，重启 SillyTavern 服务器以重新初始化分词器。

如果所需的分词器模型未缓存且下载已禁用，则将使用回退分词器（Llama 3）进行计数。

### 令牌填充

> **📝 适用于：文本补全 API**
>
> SillyTavern 将始终为聊天补全模型使用匹配的分词器，因此无需令牌填充。


除非 SillyTavern 使用运行模型的远程后端 API 提供的分词器，否则在提示生成期间假定的所有令牌计数均基于所选 [分词器](#tokenizer) 类型进行估算。

由于在接近模型定义最大值的上下文大小下，分词结果可能不准确，因此提示的某些部分可能会被裁剪或丢弃，这可能会对角色定义的一致性产生负面影响。

为防止这种情况，SillyTavern 会分配一部分上下文大小作为填充，以避免添加超出模型容纳能力的聊天条目。如果你发现即使选择了最匹配的分词器，提示的某些部分仍被裁剪，请调整填充以使描述不被截断。

你可以输入负值进行反向填充，这允许分配超过设定的最大令牌数量。