
# VRM

本指南将带你逐步完成 SillyTavern 中 VRM 扩展的设置与自定义。该扩展允许你为角色使用 VRM 动画模型，为虚拟角色增添动态与交互元素。

## 前提条件

在开始之前，请确保满足以下前提条件：

1. **分支选择**：确保你使用的是 SillyTavern 的最新版本分支，以获取最新功能与更新。

2. **扩展安装**：在扩展面板（由堆叠方块图标表示）的“下载扩展与资源”菜单中安装“VRM”扩展。

3. **模型文件夹放置**：将你的 VRM 模型文件（.vrm）放入 `/data/<用户句柄>/assets/vrm/model` 目录，动画文件放入 `/data/<用户句柄>/assets/vrm/animation` 目录。当前支持的动画文件格式为与 VRM 模型兼容的 .fbx 和 .bvh。这包括你从 Mixamo (https://www.mixamo.com/) 获取的任何动画，以及从 XR Animator (https://github.com/ButzYung/SystemAnimatorOnline) 等工具导出的任何动画。

## 扩展设置

VRM 扩展提供了多种设置，用于自定义动画模型的行为。以下是关键设置：

![UI 全局设置](/static/extensions/vrm-global.png)

### 全局设置

1. **启用**：
   - 勾选此复选框可激活扩展，使 VRM 模型能在 SillyTavern 中交互。
   - 如果只想使用普通精灵，可以禁用此扩展。

2. **注视相机**：
   - 勾选此复选框可使 VRM 模型的眼睛注视相机。

3. **眨眼**：
   - 勾选此复选框可使 VRM 模型以随机间隔眨眼。模型的表情应正确定义眨眼权重属性，否则模型可能会闭眼眨眼。例如，如果发生这种情况，要么：
     - 如果你有 .vroid 文件，修正模型；
     - 不使用该不正确面部表情；
     - 通过此复选框完全禁用眨眼。

4. **TTS 口型同步**
   - 勾选此复选框可使 VRM 嘴部运动跟随播放 TTS 时的声音。仅适用于 SillyTavern 自行播放声音的 TTS（如 XTTS，非流式模式）。若禁用，则当收到新角色消息时，嘴部将根据消息文本长度进行动画。

5. **自动发送交互**：
   - 勾选此复选框可在点击带有映射消息的区域时自动触发角色交互（详见命中区域部分）。

### 性能设置

1. **身体碰撞箱**
   - 勾选此复选框可激活对 VRM 模型多个部位的点击检测，根据模型可检测以下区域：头部/胸部/手部/腹股沟/臀部/腿部/脚部。碰撞箱位置每帧计算并跟随身体动画，禁用此选项可提升性能。

2. **使用模型缓存**
   - 勾选此复选框可在切换模型时将 VRM 模型保留在内存中，从而更快切换回之前的模型。例如，当同一角色使用不同模型更换服装或形态时很有用。可能影响性能。

3. **使用动画缓存**
   - 勾选此复选框可将会话期间播放的所有动画保留在内存中。分配给模型的所有动画也会在模型首次出现时加载。这会增加首次加载模型的时间，但可使所有动画切换瞬间完成。可能影响性能。

### 调试设置

1. **显示网格**
   - 勾选此复选框可可视化 3D 网格、模型拖动框和身体碰撞箱。

2. **重新加载按钮**
   - 点击此按钮可重新加载 3D 场景，清除缓存和所有 VRM 模型。如果出现错误或缓存开始影响性能时使用。

### 场景设置

![UI 场景设置](/static/extensions/vrm-scene.png)

1. **灯光颜色**
   - 设置 3D 场景中灯光的颜色。点击重置按钮将其恢复为默认的白色。根据浏览器不同，你可以使用颜色选择器，例如从背景图像中取色以增加沉浸感。

2. **灯光强度**
   - 使用滑块以百分比设置灯光强度。点击重置按钮将其恢复为默认值 100%。VRM 模型对灯光的反应可能因模型内置的烘焙着色器而异，可自行调整数值观察效果。

![UI 模型设置](/static/extensions/vrm-model.png)

## 角色选择

这些设置允许你管理角色并为它们分配 VRM 模型。

1. **刷新按钮**：
   - 点击刷新按钮更新当前聊天中的角色列表。

2. **选择角色**：
   - 使用下拉列表选择要分配 VRM 模型的角色。

3. **移除按钮**：
   - 点击此按钮删除已分配给角色的模型。

## 模型选择

1. **刷新按钮**：
   - 如果你的 VRM 模型没有出现在列表中，请点击刷新按钮。

2. **选择模型**：
   - 从列表中选择一个模型，将其分配给选中的角色。
   - 模型必须位于 `/data/<用户句柄>/assets/vrm/model` 目录中。

3. **重置按钮**
   - 点击此按钮将模型设置重置为默认值。如果你有与默认值对应的动画文件，它们将自动映射。参见本README末尾的命名映射。

## 模型设置

1. **模型缩放**：
   - 使用滑块调整模型的大小，使其变大或变小。

2. **模型中心 X/Y 偏移**：
   - 使用这些滑块更改模型相对于窗口中心的水平/垂直位置。

3. **模型 X/Y 旋转**
   - 使用这些滑块更改模型相对于模型臀部的水平/垂直旋转。

### 备注
   - 设置按模型保存，而非按角色保存，并在不同聊天中保留。
   - 如果要对两个不同的角色使用相同的模型但使用不同的设置，请复制 .vrm 文件。
   - 你也可以用鼠标拖动模型，这些设置将随之更新并保存。左键单击并按住可在屏幕上拖动模型。中键单击并按住可旋转模型，或使用 Shift+左键。将鼠标指针放在模型上滚动滚轮可缩放模型，或使用 Ctrl+左键。
   - 如果模型意外移出视野，可使用这些 UI 设置将其重新带回屏幕。同时，勾选“显示框架”复选框可清晰看到可点击拖动的区域。

![UI 命中区域设置](/static/extensions/vrm-hitboxes.png)

## 命中区域映射

   - 根据模型骨骼定义，可生成一些命中区域。它们将列在 UI 的这一部分中，你可以为每个区域分配一个表情/动画/消息，点击该区域时将触发。

![UI 分类设置](/static/extensions/vrm-classify.png)

## 分类表情映射

1. **要求**
   - 需要安装 classify expression 扩展；否则将回退到默认动画。

2. **映射**
   - 对于 classify 扩展检测到的每种情绪，你可以分配一个表情/动作/消息。消息可以包含命令。

## 命令

1. **/vrmlightcolor**
   - 设置灯光颜色
   - 参数：颜色
   - 示例："/vrmlightcolor white" 或 "/vrmlightcolor purple"。
2. **/vrmlightintensity**
   - 设置灯光强度百分比
   - 参数：强度
   - 示例："/vrmlightintensity 0" 或 "/vrmlightintensity 100"
3. **/vrmmodel**
   - 将 VRM 模型分配给角色
   - 参数：角色, 模型
   - 示例：单人聊天中 "/vrmmodel Seraphina.vrm" 或群聊中 "/vrmmodel character=Seraphina model=Seraphina.vrm"
4. **/vrmexpression**
   - 更改模型的表情
   - 参数：角色, 表情
   - 示例：单人聊天中 "/vrmexpression happy" 或群聊中 "/vrmexpression character=Seraphina expression=happy"

5. **/vrmmotion**
   - 更改模型的动画
   - 参数：角色, 动作, 循环, 随机
   - "/vrmmotion idle" 或 "/vrmmotion character=Seraphina motion=idle loop=true random=false"

## 动画默认映射
如果你的动画文件按以下方式命名，则当重置模型设置时会自动映射。例如，文件名为 "assets/vrm/animation/neutral.bvh" 和 "assets/vrm/animation/neutral1.fbx" 将自动作为 default 和 neutral 分类动画的组进行映射。命中区域同理。

    // 回退
    "default": "assets/vrm/animation/neutral",

    // 分类类别
    "admiration": "assets/vrm/animation/admiration",
    "amusement": "assets/vrm/animation/amusement",
    "anger": "assets/vrm/animation/anger",
    "annoyance": "assets/vrm/animation/annoyance",
    "approval": "assets/vrm/animation/approval",
    "caring": "assets/vrm/animation/caring",
    "confusion": "assets/vrm/animation/confusion",
    "curiosity": "assets/vrm/animation/curiosity",
    "desire": "assets/vrm/animation/desire",
    "disappointment": "assets/vrm/animation/disappointment",
    "disapproval": "assets/vrm/animation/disapproval",
    "disgust": "assets/vrm/animation/disgust",
    "embarrassment": "assets/vrm/animation/embarrassment",
    "excitement": "assets/vrm/animation/excitement",
    "fear": "assets/vrm/animation/fear",
    "gratitude": "assets/vrm/animation/gratitude",
    "grief": "assets/vrm/animation/grief",
    "joy": "assets/vrm/animation/joy",
    "love": "assets/vrm/animation/love",
    "nervousness": "assets/vrm/animation/nervousness",
    "neutral": "assets/vrm/animation/neutral",
    "optimism": "assets/vrm/animation/optimism",
    "pride": "assets/vrm/animation/pride",
    "realization": "assets/vrm/animation/realization",
    "relief": "assets/vrm/animation/relief",
    "remorse": "assets/vrm/animation/remorse",
    "sadness": "assets/vrm/animation/sadness",
    "surprise": "assets/vrm/animation/surprise",

    // 命中区域
    "head": "assets/vrm/animation/hitarea_head",
    "chest": "assets/vrm/animation/hitarea_chest",
    "groin": "assets/vrm/animation/hitarea_groin",
    "butt": "assets/vrm/animation/hitarea_butt",
    "leftHand": "assets/vrm/animation/hitarea_hands",
    "rightHand": "assets/vrm/animation/hitarea_hands",
    "leftLeg": "assets/vrm/animation/hitarea_leg",
    "rightLeg": "assets/vrm/animation/hitarea_leg",
    "rightFoot": "assets/vrm/animation/hitarea_foot",
    "leftFoot": "assets/vrm/animation/hitarea_foot"

感谢你遵循本指南！你的 SillyTavern 体验现已因动画与交互式 3D 模型而更加丰富。

## 备注
   - 此扩展加载的 VRM 模型是 .vrm 文件，而非 .vroid 文件。
   - 动画文件应与 VRM 兼容，你可以使用 XR animation (https://github.com/ButzYung/SystemAnimatorOnline) 等工具转换 fbx/bvh 动画文件。
   - 你可以通过将文件名相同但末尾数字不同（例如 "idle1.bvh"、"idle2.bvh"、"idle3.bvh"）的文件视为一个组 "idle"，当在映射中选中时，触发时会随机播放其中一个，可用于增加动画多样性。
   - 你可从此仓库获取精选动画：https://github.com/test157t/VRM-Animations-Pack-For-Silly-Tavern
   - Nitral 有一些关于如何使用该扩展和动画仓库的教程视频：https://www.youtube.com/@nitralai