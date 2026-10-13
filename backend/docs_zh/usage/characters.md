
# 角色

角色是您可以创建和管理的AI身份，用于塑造AI在对话中的角色。每个角色都有名称、个性和对话历史。您可以创建任意数量的角色，并在它们之间随时切换。

角色可以在单人聊天中使用，也可以向群组聊天中添加多个角色，让它们彼此互动。

## 角色管理面板

从导航栏打开 <i class="fa-solid fa-address-card"></i> **角色** 面板，可以访问角色列表。点击某个角色或群组即可与之聊天或进行编辑，或者选择 <i class="fa-solid fa-user-plus"></i> **创建新角色** 来添加一个新角色。

### 面板控件

* <i class="fa-solid fa-lock"></i> **固定面板**：交互时保持面板打开
* <i class="fa-solid fa-list-ul"></i> **角色列表**：返回角色列表视图
* **快速切换栏**：快速访问常用角色

### 角色列表

* <i class="fa-solid fa-user-plus"></i> **创建新角色**：添加一个新角色
* <i class="fa-solid fa-file-import"></i> **导入角色**：从文件加载角色
* <i class="fa-solid fa-cloud-arrow-down"></i> **外部导入**：从URL导入
* <i class="fa-solid fa-users-gear"></i> **创建群组**：开始新的群组聊天

#### 搜索与排序

* **搜索栏**：按名称或属性过滤角色
* **排序下拉菜单**：多种排序选项：
    - 按字母顺序 (A-Z, Z-A)
    - 按时间顺序 (最新, 最旧)
    - 按使用情况 (最近, 最多/最少聊天)
    - 按大小 (最多/最少Token)
    - 特殊 (收藏, 随机)

#### 按类型或标签过滤角色

* <i class="fa-solid fa-star"></i> **收藏过滤**：显示收藏角色
* <i class="fa-solid fa-users"></i> **群组过滤**：仅显示群组聊天
* <i class="fa-solid fa-folder-plus"></i> **标签作为文件夹**：按标签层级组织
* <i class="fa-solid fa-gear"></i> **管理标签**：[标签配置](/usage/core-concepts/tags/)
* <i class="fa-solid fa-tags"></i> **标签列表**：查看所有可用标签
* <i class="fa-solid fa-filter-circle-xmark"></i> **清除过滤**：重置所有过滤条件

### 角色创建/编辑面板

* **头像图片**：上传并预览角色形象图片
* **Token计数**：该角色的[Token用量](/usage/core-concepts/characterdesign/#character-tokens)
* <i class="fa-solid fa-ranking-star"></i> **统计**：聊天历史和使用统计
* [标签管理](/usage/core-concepts/tags/)

#### 快捷操作

- <i class="fa-solid fa-star"></i> 收藏开关
- <i class="fa-solid fa-book"></i> 高级定义
- <i class="fa-solid fa-globe"></i> [角色世界观](/usage/core-concepts/worldinfo/#character-lore)
- <i class="fa-solid fa-passport"></i> [聊天世界观](/usage/core-concepts/worldinfo/#chat-lorebook)：将聊天与世界信息关联
- <i class="fa-solid fa-file-export"></i> 导出角色
- <i class="fa-solid fa-clone"></i> 复制
- <i class="fa-solid fa-skull"></i> 删除

#### 扩展选项

* 世界信息关联
* 卡片世界观导入
* 场景覆盖
* 人格转换
* 角色重命名
* 源关联
* 替换/更新
* 标签导入
* 画廊视图

#### 内容字段

* **[角色描述](/usage/core-concepts/characterdesign/#character-description)**：角色简要总结
* **[初始消息](/usage/core-concepts/characterdesign/#first-message)**：开始新聊天时的初始问候语或提示
* **备选问候语**：定义多个初始消息，在开始聊天时可以通过滑动切换

### 高级定义面板

点击 <i class="fa-solid fa-book"></i> **高级定义** 按钮，可进入扩展角色设置。

#### 提示覆盖（聊天补全/指令模式）

* **主提示**：替换默认的[主提示/系统提示](/usage/prompts/#main-prompt-system-prompt)，可以使用\{\{original\}\}占位符包含原始提示
* **历史后指令**：覆盖默认的[历史后指令](/usage/prompts/#post-history-instructions)

#### 创建者元数据

关于角色的非提示信息：

- 创建者名称/联系方式
- 角色版本
- 创建者注释
- 嵌入标签列表

#### 角色个性

* **[个性摘要](/usage/core-concepts/characterdesign/#personality-summary)**：角色特征简要概述
* **[场景](/usage/core-concepts/characterdesign/#scenario)**：对话的背景和情境
* **角色备注**：自定义消息，可选择深度和消息角色（另请参阅[作者备注](/usage/core-concepts/authors-note/)）
* **话多程度**（群组聊天）：滑块，范围从 害羞 → 正常 → 健谈
* **示例消息**：角色写作风格的示例

### 群组聊天管理

如果是群组聊天，您可以从该面板管理群组成员和设置。

更多详情请参见[群组聊天](/usage/core-concepts/groupchats/)。