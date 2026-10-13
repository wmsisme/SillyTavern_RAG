
# 宏

> **💡 实验性宏引擎**
>
> 实验性宏引擎支持嵌套、稳定的替换顺序及其他改进。新安装默认启用。现有安装可在 **用户设置** > **聊天/消息处理** > **实验性宏引擎** 中启用。


宏是动态占位符，在处理文本时会被替换为实际值。它们在整个 SillyTavern 中用于提示词、角色卡、世界书、快速回复等。

## 查找可用宏

SillyTavern 为所有可用宏提供内置文档：

- **斜杠命令**：在聊天输入框中输入 `/? macros` 可显示所有已注册宏及其描述的列表。
- **自动补全**：有关输入时获取建议的详细信息，请参见下面的[宏自动补全](#宏自动补全)。

### 宏自动补全

宏自动补全会在您键入时提供可用宏的建议。它适用于 SillyTavern 中所有支持宏的文本字段。

输入 `{{` 即可触发宏的自动补全，显示可用宏及其参数、可能的[宏标志](#宏标志)、[变量简写](#变量简写)等。

**默认出现自动补全的位置：**

- 聊天用户输入框
- 扩展编辑器（全屏文本编辑，通过文本字段旁边的“展开”按钮打开）
- 提示词管理器编辑器

**在其他字段触发自动补全：**

- 在任何支持宏的文本字段中按 **Ctrl+Space** 打开自动补全弹窗
- 启用 **设置 → 自动补全设置 → 在所有宏字段中显示**，可在所有宏字段中自动显示自动补全

## 基本语法

宏用双花括号包裹：

```txt
{{macroName}}
```

宏名称**不区分大小写**。`{{User}}`、`{{USER}}` 和 `{{user}}` 解析为同一个宏。

示例：

```txt
{{user}}        // 返回当前用户/角色名称
{{char}}        // 返回当前角色名称
{{time}}        // 返回当前时间
{{date}}        // 返回当前日期
```

## 参数

许多宏接受参数来自定义其行为。

### 空格分隔符

对于只有一个参数的宏，可以用空格分隔宏名称与其参数：

```txt
{{macroName argument}}
```

示例：

```txt
{{getvar myVariable}}
{{roll 1d20}}
{{reverse Hello World}}
```

### 双冒号分隔符

使用 `::` 分隔多个参数：

```txt
{{macroName::arg1::arg2::arg3}}
```

示例：

```txt
{{setvar::myVariable::Hello World}}
{{random::red::green::blue}}
{{roll::2d6+3}}
```

空格和 `::` 都是宏参数的推荐语法。

### 单冒号分隔符（旧式）

单个 `:` 也可以引入参数，但此语法被视为旧式，不推荐用于新内容：

```txt
{{macroName:argument}}
```

示例：

```txt
{{roll:1d20}}
```

## 宏定义中的空白符

宏名称、分隔符和参数之间的空白符将被忽略。这允许更易读的格式：

```txt
{{ macroName :: arg1 :: arg2 }}
{{ setvar :: myVariable :: some value }}
{{ if :: condition }}
```

以上所有形式都等效于没有额外空格的紧凑形式。

## 嵌套宏

宏可以嵌套在其他宏内部。内部宏首先被解析：

```txt
{{getvar::{{char}}_mood}}
```

这首先解析 `{{char}}`（例如为“Alice”），然后解析 `{{getvar::Alice_mood}}`。

更多示例：

```txt
{{setvar::greeting::Hello, {{user}}!}}
```

设置一个包含用户名称的变量。

```txt
{{if {{getvar::showDetails}}}}Details here{{/if}}
```

条件本身是一个检索变量值的宏。

## 作用域宏

任何至少接受一个参数的宏都支持作用域语法。开闭标签之间的内容成为宏的**最后一个参数**。

### 作用域语法

无需将最后一个参数内联写出，而是可以将其放在开闭标签之间：

```txt
{{macroName argument}}
  scoped content here
{{/macroName}}
```

闭标签在宏名称前使用 `/` 标志：`{{/macroName}}`。

这等效于：

```txt
{{macroName::argument::scoped content here}}
```

### 示例

设置一个包含多行内容的变量：

```txt
{{ setvar backstory }}
  This character was born in a small village
  and grew up to become a renowned scholar.
{{ /setvar }}
```

使用带有作用域内容的 `reverse`：

```txt
{{ reverse }}
  Hello World
{{ /reverse }}
```

返回“dlroW olleH”。

### 内容修剪

默认情况下，作用域内容会被自动修剪：

- 移除前导和尾随空白
- 一致的缩进会被取消缩进（第一行非空行的缩进会从所有行中移除）

这允许干净的格式：

```txt
{{ if condition }}
    # Heading
    Some content here
{{ /if }}
```

生成 `# Heading\nSome content here`（不含前导空格）。

若要保留所有空白符（包括前导/尾随换行符），请使用 `#` 标志。详见[宏标志](#宏标志)。

## 条件宏

`{{if}}` 宏根据值是真值还是假值，有条件地渲染内容。

### 简单条件

```txt
{{ if description }}
  # Character Description
  {{ description }}
{{ /if }}
```

仅在 `description` 返回非空值时显示标题和描述。

条件可以是：

- 宏名称（如果无需参数则自动解析）
- 来自嵌套宏的任何值，如 `{{getvar::flag}}`
- 变量简写，如 `.myFlag` 或 `$globalFlag`（参见[变量简写](#变量简写)）
- 任何文本（将根据其内容隐式解析为真值或假值）

假值：空字符串、`false`、`0`、`off`、`no`。

### 在条件中使用变量简写

变量简写提供了一种简洁的方式来检查条件中的变量值：

```txt
{{ if .isEnabled }}
  Feature is enabled.
{{ /if }}

{{ if !$globalDisabled }}
  Not globally disabled.
{{ /if }}
```

关于简写符号的更多细节，参见[变量简写](#变量简写)。

### 否定条件

在条件前加 `!` 来取反：

```txt
{{ if !personality }}
  No personality defined for this character.
{{ /if }}
```

### If/Else 分支

在 `{{if}}` 块内部使用 `{{else}}` 来定义替代分支：

```txt
{{ if personality }}
  {{ personality }}
{{ else }}
  No personality defined.
{{ /if }}
```

另一个示例：

```txt
{{ if {{getvar::details-block}} }}
  # Details Block
  {{ getvar::details-block }}
{{ else }}
  No details currently exist.
{{ /if }}
```

## 宏标志

标志是放在开括号和宏名称之间的特殊符号字符，用于修改宏的行为。

### 语法

```txt
{{!macroName}}
{{#macroName}}
```

标志可以组合：

```txt
{{!?macroName}}
```

标志和宏名称之间允许空白符：

```txt
{{ / macroName }}
{{ # macroName }}
```

### 已实现的标志

| 标志 | 名称 | 描述 |
|------|------|-------------|
| `/` | 关闭块 | 标记作用域宏的闭合标签。示例：`{{/if}}` |
| `#` | 保留空白符 | 防止作用域内容自动修剪。 |

### 计划中的标志（尚未实现）

| 标志 | 名称 | 描述 |
|------|------|-------------|
| `!` | 立即 | 在相同文本中的其他宏之前解析此宏。 |
| `?` | 延迟 | 在相同文本中的其他宏之后解析此宏。 |
| `~` | 重新评估 | 标记此宏进行重新评估。 |
| `>` | 过滤 | 为此宏启用基于管道的输出过滤器。 |

### 类似标志的前缀运算符

变量简写语法使用前缀运算符（`.` 和 `$`），其行为类似于标志，但本身不是标志。  
详见[变量简写](#变量简写)部分。

### 保留空白符标志

当需要保留作用域内容中的所有空白符（包括前导/尾随换行符和缩进）时，请使用 `#` 标志：

```txt
{{ # setvar code }}
    function hello() {
        return "world";
    }
{{ /setvar }}
```

不使用 `#` 时，内容会被修剪和取消缩进。使用 `#` 时，所有空白符（包括开标签后和闭标签前的换行符）将被原样保留。

## 注释

使用注释宏来添加不会出现在输出中的注释：

```txt
{{// This is a comment and will be removed}}
```

对于多行注释，使用作用域语法：

```txt
{{ // }}
  This entire block is a comment.
  It can span multiple lines.
{{ /// }}
```

## 转义宏

要显示字面花括号而不进行宏解析，请使用反斜杠转义：

```txt
\{\{notAMacro\}\}
```

这会以纯文本形式输出 `{{notAMacro}}`。

## 变量简写

变量简写为常见的变量操作提供了简洁的语法。使用 `.` 表示局部变量，使用 `$` 表示全局变量。

### 变量简写前缀

| 前缀 | 名称 | 描述 |
| ------ | --------------- | --------------------------------------------------------------- |
| `.` | 局部变量 | 局部变量操作的简写。示例：`{{.myvar}}` |
| `$` | 全局变量 | 全局变量操作的简写。示例：`{{$myvar}}` |

这些前缀运算符必须**紧接在**变量名称之前，位于任何可选出现的[宏标志](#宏标志)之后。它们不被视为宏标志，而是指示正在插入变量简写而非按名称引用宏的指示符。前缀运算符不是变量名称本身的一部分，而是改变变量访问方式的修饰符。

### 变量名称

变量名称遵循与宏标识符相同的规则：以字母开头，后跟字母、数字、下划线或连字符。最后一个字符不能是下划线或连字符。

```txt
{{.my-var}}       // 有效
{{.my_var}}       // 有效
{{.myVar123}}     // 有效
```

如果您的变量标识符不符合标准规则，则必须使用完整的变量宏语法（例如 `{{getvar::my§var----}}`），或者重命名/迁移您的变量值。

### 值中的嵌套宏

变量值可以包含嵌套宏：

```txt
{{.greeting = Hello, {{user}}!}}
```

解析为一个保存了 `Hello, User!` 的变量（如果 `{{user}}` 名为“User”）。

### 空白符处理

运算符周围的空白符是允许的：

```txt
{{ .myvar = spaced value }}
{{ .counter ++ }}
```

### 变量简写运算符

以下运算符可与变量简写一起使用。每个运算符遵循模式 `{{.varName operator value}}` 或 `{{$varName operator value}}`。

| 运算符 | 名称 | 示例 | 描述 |
| -------- | ------------------------- | ---------------------- | ------------------------------------------------------ |
| *(无)* | [获取](#获取变量) | `{{.myvar}}` | 返回变量值 |
| `=` | [设置](#设置变量) | `{{.myvar = value}}` | 设置变量值，不返回任何内容 |
| `++` | [递增](#递增) | `{{.counter++}}` | 增加 1，返回新值 |
| `--` | [递减](#递减) | `{{.counter--}}` | 减少 1，返回新值 |
| `+=` | [加法](#加法) | `{{.score += 10}}` | 向变量添加值（数字或字符串拼接），不返回任何内容 |
| `-=` | [减法](#减法) | `{{.health -= 5}}` | 从变量减去值（仅数字），不返回任何内容 |
| `\|\|` | [逻辑或](#逻辑或) | `{{.name \|\| Guest}}` | 变量为假值时返回备选 |
| `??` | [空值合并](#空值合并) | `{{.name ?? Guest}}` | 仅当变量未定义时返回备选 |
| `\|\|=` | [逻辑或赋值](#逻辑或赋值) | `{{.name \|\|= Guest}}` | 变量为假值时设置值，返回新值 |
| `??=` | [空值合并赋值](#空值合并赋值) | `{{.name ??= Guest}}` | 仅当变量未定义时设置值，返回新值 |
| `==` | [等于](#等于) | `{{.status == active}}` | 比较值，返回 `"true"` 或 `"false"` |
| `!=` | [不等于](#不等于) | `{{.status != active}}` | 比较值，如果不相等返回 `"true"` |
| `>` | [大于](#大于) | `{{.score > 50}}` | 如果变量大于值返回 `"true"` |
| `>=` | [大于等于](#大于等于) | `{{.level >= 10}}` | 如果变量大于等于值返回 `"true"` |
| `<` | [小于](#小于) | `{{.health < 20}}` | 如果变量小于值返回 `"true"` |
| `<=` | [小于等于](#小于等于) | `{{.health <= 0}}` | 如果变量小于等于值返回 `"true"` |

#### 获取变量

使用简单前缀检索变量值：

```txt
{{.myvar}}       // 获取局部变量 "myvar"
{{$myvar}}       // 获取全局变量 "myvar"
```

等效于 `{{getvar::myvar}}` 和 `{{getglobalvar::myvar}}`。

#### 设置变量

使用 `=` 运算符设置变量值：

```txt
{{ .myvar = Hello World }}     // 设置局部变量
{{ $myvar = Some value }}      // 设置全局变量
```

等效于 `{{setvar::myvar::Hello World}}` 和 `{{setglobalvar::myvar::Hello World}}`。返回空字符串。

#### 递增

使用 `++` 将数值变量增加 1：

```txt
{{.counter++}}    // 递增局部变量，返回新值
{{$counter++}}    // 递增全局变量，返回新值
```

等效于 `{{incvar counter}}` 和 `{{incglobalvar counter}}`。返回递增后的新值。

#### 递减

使用 `--` 将数值变量减少 1：

```txt
{{.counter--}}    // 递减局部变量，返回新值
{{$counter--}}    // 递减全局变量，返回新值
```

等效于 `{{decvar counter}}` 和 `{{decglobalvar counter}}`。返回递减后的新值。

#### 加法

使用 `+=` 向变量添加数值：

```txt
{{.score += 10}}     // 向局部变量加 10
{{$total += 5}}      // 向全局变量加 5
```

等效于 `{{addvar::score::10}}` 和 `{{addglobalvar::total::5}}`。返回空字符串。

加法运算符还支持将字符串附加到现有字符串变量，前提是两者都不是数字：

```txt
{{.myvar += {{noop}} | Second block}}   // 如果变量之前是 "Content"，则解析为 "Content | Second block"
                                        // 使用 `{{noop}}` 来添加否则会被自动修剪的空白符。
```

#### 减法

使用 `-=` 从变量中减去数值：

```txt
{{.health -= 10}}    // 从局部变量减 10
{{$points -= 5}}     // 从全局变量减 5
```

等效于 `{{addvar::score::10}}` 和 `{{addglobalvar::total::5}}`，但使用负数/取反后的数字。返回空字符串。
如果值不是有效数字，则记录警告且变量不变。

#### 逻辑或

使用 `||` 在变量为假值（空字符串、`0`、`false`）时提供备选值：

```txt
{{.name || Anonymous}}     // 如果 .name 为空或假值，返回 "Anonymous"
{{$setting || default}}    // 如果 $setting 为假值，返回 "default"
```

如果变量为真值则返回变量值，否则返回备选值。备选**仅在需要时求值**（延迟求值）。

#### 空值合并

使用 `??` 仅在变量不存在时提供备选值：

```txt
{{.name ?? Guest}}         // 仅当 .name 未定义时返回 "Guest"
{{$config ?? default}}     // 仅当 $config 不存在时返回 "default"
```

与 `||` 不同，即使变量为假值（空字符串、`0`、`false`），只要变量存在，就返回该值。备选**仅在需要时求值**（延迟求值）。

#### 逻辑或赋值

使用 `||=` 仅在变量当前为假值时设置值：

```txt
{{.name ||= Anonymous}}    // 如果 .name 为假值，设置并返回 "Anonymous"
{{$count ||= 0}}           // 如果 $count 为假值，设置并返回 "0"
```

如果变量已为真值，则返回当前值而不修改。返回最终值（现有或新设置）。

#### 空值合并赋值

使用 `??=` 仅在变量不存在时设置值：

```txt
{{.name ??= Guest}}        // 仅当 .name 未定义时设置并返回 "Guest"
{{$config ??= default}}    // 仅当 $config 不存在时设置并返回 "default"
```

与 `||=` 不同，如果变量已存在，则保留假值（空字符串、`0`、`false`）。返回最终值（现有或新设置）。

#### 等于

使用 `==` 比较变量值与另一个值：

```txt
{{.status == active}}      // 如果 .status 等于 "active" 返回 "true"，否则 "false"
{{$mode == dark}}          // 如果 $mode 等于 "dark" 返回 "true"，否则 "false"
```

执行字符串比较并返回字面字符串 `"true"` 或 `"false"`。  
将不存在的变量、null 变量和空变量视为相同。

在 `{{if}}` 条件中很有用：

```txt
{{if {{.status == active}} }}Active mode{{/if}}
```

#### 不等于

使用 `!=` 比较变量值与另一个值是否不相等：

```txt
{{.status != inactive}}    // 如果 .status 不等于 "inactive" 返回 "true"，否则 "false"
{{$mode != light}}         // 如果 $mode 不等于 "light" 返回 "true"，否则 "false"
```

执行字符串比较，如果值不同返回 `"true"`，如果相等返回 `"false"`。  
将不存在的变量、null 变量和空变量视为相同。

在 `{{if}}` 条件中很有用：

```txt
{{if {{.status != disabled}} }}Feature enabled{{/if}}
```

#### 大于

使用 `>` 检查变量的数值是否大于另一个值：

```txt
{{.score > 50}}        // 如果 .score 大于 50 返回 "true"
{{$level > 5}}         // 如果 $level 大于 5 返回 "true"
```

执行数值比较并返回字面字符串 `"true"` 或 `"false"`。

在 `{{if}}` 条件中很有用：

```txt
{{if {{.score > 100}} }}High score!{{/if}}
```

#### 大于等于

使用 `>=` 检查变量的数值是否大于或等于另一个值：

```txt
{{.level >= 10}}       // 如果 .level 至少为 10 返回 "true"
{{$points >= 100}}     // 如果 $points 为 100 或更多返回 "true"
```

执行数值比较并返回字面字符串 `"true"` 或 `"false"`。

在 `{{if}}` 条件中很有用：

```txt
{{if {{$level >= 10}} }}Unlocked advanced features{{/if}}
```

#### 小于

使用 `<` 检查变量的数值是否小于另一个值：

```txt
{{.health < 20}}       // 如果 .health 低于 20 返回 "true"
{{$timer < 0}}         // 如果 $timer 为负返回 "true"
```

执行数值比较并返回字面字符串 `"true"` 或 `"false"`。

在 `{{if}}` 条件中很有用：

```txt
{{if {{.health < 20}} }}Low health warning!{{/if}}
```

#### 小于等于

使用 `<=` 检查变量的数值是否小于或等于另一个值：

```txt
{{.health <= 0}}       // 如果 .health 为 0 或更低返回 "true"
{{$attempts <= 3}}     // 如果 $attempts 为 3 或更少返回 "true"
```

执行数值比较并返回字面字符串 `"true"` 或 `"false"`。

在 `{{if}}` 条件中很有用：

```txt
{{if {{.health <= 0}} }}Game over{{/if}}
```

## 旧式语法

为了向后兼容，仍支持尖括号标记：

| 旧式 | 等效宏 |
|--------|------------------|
| `<USER>` | `{{user}}` |
| `<BOT>` | `{{char}}` |
| `<CHAR>` | `{{char}}` |
| `<GROUP>` | `{{group}}` |
| `<CHARIFNOTGROUP>` | `{{charIfNotGroup}}` |

这些在处理过程中会自动转换为等效宏。

> **注意：** 不推荐使用旧式语法。新内容请使用等效的 `{{macro}}` 语法。

## 按类别划分的常见宏

> **💡 Tip**
>
> 输入 `/? macros` 获取完整可用宏列表及其详细说明。


### 名称与参与者

| 宏 | 描述 |
|-------|-------------|
| `{{user}}` | 当前用户/角色名称 |
| `{{char}}` | 当前角色名称 |
| `{{group}}` | 组成员名称逗号分隔列表（包括静音成员），单人聊天中返回角色名称 |
| `{{groupNotMuted}}` | 组成员名称逗号分隔列表，排除静音成员 |
| `{{charIfNotGroup}}` | 角色名称（群组中为空） |
| `{{notChar}}` | 除当前发言者之外所有参与者的逗号分隔列表 |

### 角色卡与角色字段

| 宏 | 描述 |
|-------|-------------|
| `{{description}}` | 角色描述 |
| `{{personality}}` | 角色个性 |
| `{{scenario}}` | 角色场景 |
| `{{persona}}` | 用户角色描述 |
| `{{charPrompt}}` | 角色的主提示词覆盖 |
| `{{charInstruction}}` | 角色的历史后指令覆盖 |
| `{{charDepthPrompt}}` | 角色的 @ 深度笔记 |
| `{{charCreatorNotes}}` | 角色卡中的创建者注释 |
| `{{charVersion}}` | 角色的版本号 |
| `{{mesExamples}}` | 角色的对话示例，格式化为指令模式 |
| `{{mesExamplesRaw}}` | 来自角色卡的未格式化对话示例 |
| `{{charFirstMessage}}` | 角色的第一条消息（问候语）。接受可选索引用于备选问候语，例如 `{{charFirstMessage::1}}` |
| `{{original}}` | 用于角色提示词覆盖中的原始消息内容 |

### 聊天历史与消息

| 宏 | 描述 |
|-------|-------------|
| `{{lastMessage}}` | 聊天中的最后一条消息 |
| `{{lastMessageId}}` | 聊天中最后一条消息的索引 |
| `{{lastUserMessage}}` | 聊天中最后一条用户消息 |
| `{{lastCharMessage}}` | 聊天中最后一条角色/机器人消息 |
| `{{firstIncludedMessageId}}` | 包含在当前上下文中的第一条消息的索引 |
| `{{firstDisplayedMessageId}}` | 聊天中显示的第一条消息的索引 |
| `{{lastSwipeId}}` | 最后一条消息的最后一次划动基于1的索引 |
| `{{currentSwipeId}}` | 当前划动基于1的索引 |
| `{{allChatRange}}` | 提供整个聊天的范围（例如 `0-{{lastMessageId}}`），对于接受消息范围的命令很有用 |
| `{{summary}}` | 来自“摘要”扩展的最新聊天摘要（可用时） |

### 时间与日期

| 宏 | 描述 |
|-------|-------------|
| `{{time}}` | 当前本地时间 |
| `{{time::UTC±(offset)}}` | 带 UTC 偏移的时间 |
| `{{date}}` | 当前本地日期（短格式） |
| `{{weekday}}` | 当前星期几 |
| `{{isotime}}` | 当前时间，HH:mm 格式 |
| `{{isodate}}` | 当前日期，YYYY-MM-DD 格式 |
| `{{datetimeformat::format}}` | 自定义格式化日期/时间（例如 `YYYY-MM-DD HH:mm:ss`） |
| `{{idleDuration}}` | 自最后一条用户消息以来的可读时长 |
| `{{timeDiff::left::right}}` | 两个时间之间的可读差异 |

### 变量

| 宏 | 描述 |
|-------|-------------|
| `{{getvar::name}}` | 获取局部变量值 |
| `{{setvar::name::value}}` | 设置局部变量 |
| `{{addvar::name::value}}` | 向局部变量添加值（数字或字符串追加） |
| `{{incvar::name}}` | 局部变量增加 1 并返回新值 |
| `{{decvar::name}}` | 局部变量减少 1 并返回新值 |
| `{{hasvar::name}}` | 检查局部变量是否存在（返回 "true" 或 "false"） |
| `{{deletevar::name}}` | 删除局部变量 |
| `{{getglobalvar::name}}` | 获取全局变量值 |
| `{{setglobalvar::name::value}}` | 设置全局变量 |
| `{{addglobalvar::name::value}}` | 向全局变量添加值（数字或字符串追加） |
| `{{incglobalvar::name}}` | 全局变量增加 1 并返回新值 |
| `{{decglobalvar::name}}` | 全局变量减少 1 并返回新值 |
| `{{hasglobalvar::name}}` | 检查全局变量是否存在（返回 "true" 或 "false"） |
| `{{deleteglobalvar::name}}` | 删除全局变量 |

### 随机化

| 宏 | 描述 |
|-------|-------------|
| `{{random::a::b::c}}` | 随机选择（每次重新掷骰） |
| `{{pick::a::b::c}}` | 稳定随机选择（每个聊天和位置一致）。可通过 `/reroll-pick` 命令重新掷骰 |
| `{{roll::1d20}}` | 使用 droll 语法进行掷骰 |

### 运行时状态

| 宏 | 描述 |
|-------|-------------|
| `{{maxPrompt}}` | 最大提示上下文大小（提示令牌 = 上下文令牌 - 响应令牌） |
| `{{maxContextTokens}}` | 当前生成设置的最大上下文令牌数 |
| `{{maxResponseTokens}}` | 当前生成设置的最大响应令牌数 |
| `{{model}}` | 当前所选 API 的模型名称 |
| `{{isMobile}}` | 如果在移动环境运行则为 "true"，否则 "false" |
| `{{lastGenerationType}}` | 最后排队的生成请求类型（例如 "normal"、"impersonate"、"regenerate"、"quiet"、"swipe"、"continue"） |
| `{{hasExtension::name}}` | 检查扩展是否激活（返回 "true" 或 "false"）。按扩展名称匹配，不区分大小写 |

### 提示模板

| 宏 | 描述 |
|-------|-------------|
| `{{systemPrompt}}` | 活动系统提示文本（可选地由角色覆盖） |
| `{{defaultSystemPrompt}}` | 默认系统提示 |
| `{{authorsNote}}` | 作者注释的内容 |
| `{{charAuthorsNote}}` | 角色作者注释的内容 |
| `{{defaultAuthorsNote}}` | 默认作者注释的内容 |
| `{{instructStoryStringPrefix}}` | 指令故事字符串前缀 |
| `{{instructStoryStringSuffix}}` | 指令故事字符串后缀 |
| `{{instructUserPrefix}}` | 指令输入/用户前缀序列 |
| `{{instructUserSuffix}}` | 指令输入/用户后缀序列 |
| `{{instructAssistantPrefix}}` | 指令输出/助手前缀序列 |
| `{{instructAssistantSuffix}}` | 指令输出/助手后缀序列 |
| `{{instructSeparator}}` | 指令分隔符序列 |
| `{{instructSystemPrefix}}` | 指令系统前缀序列 |
| `{{instructSystemSuffix}}` | 指令系统后缀序列 |
| `{{instructFirstAssistantPrefix}}` | 指令第一个助手/输出前缀序列 |
| `{{instructLastAssistantPrefix}}` | 指令最后一个助手/输出前缀序列 |
| `{{instructFirstUserPrefix}}` | 指令第一个用户/输入前缀序列 |
| `{{instructLastUserPrefix}}` | 指令最后一个用户/输入前缀序列 |
| `{{instructStop}}` | 指令停止序列 |
| `{{instructUserFiller}}` | 指令用户对齐填充符 |
| `{{instructSystemInstructionPrefix}}` | 指令系统指令前缀序列 |
| `{{chatSeparator}}` | 文本补全提示中示例聊天块之间的分隔符 |
| `{{chatStart}}` | 文本补全提示中的聊天开始标记 |
| `{{reasoningPrefix}}` | 推理块前使用的前缀字符串 |
| `{{reasoningSuffix}}` | 推理块后使用的后缀字符串 |
| `{{reasoningSeparator}}` | 内容与响应之间的分隔符 |
| `{{charPrefix}}` | 角色的正向图像生成提示前缀 |
| `{{charNegativePrefix}}` | 角色的负向图像生成提示前缀 |

### 实用工具

| 宏 | 描述 |
|-------|-------------|
| `{{newline}}` | 插入换行符 |
| `{{newline::count}}` | 插入多个换行符 |
| `{{space}}` | 插入空格符 |
| `{{space::count}}` | 插入多个空格 |
| `{{noop}}` | 不执行任何操作，生成空字符串 |
| `{{trim}}` | 移除周围换行符 |
| `{{reverse::text}}` | 反转字符串 |
| `{{input}}` | 当前聊天输入框内容 |
| `{{banned::word}}` | 为文本补全后端禁用某个词 |
| `{{outlet::key}}` | 返回指定出口键的世界信息出口提示 |