
# STscript 语言参考

## 什么是 STscript？

它是一种简单但功能强大的脚本语言，可用于扩展 SillyTavern 的功能，而无需进行复杂的编程，它允许您：

- 创建迷你游戏或速通挑战
- 构建 AI 驱动的聊天洞察
- 释放您的创造力并与他人分享

STscript 基于斜杠命令引擎构建，利用命令批处理、数据管道、宏和变量。
这些概念将在以下文档中描述。

### 安全注意事项

能力越大，责任越大。请保持谨慎，并在执行脚本前始终检查它们。

## Hello, World！

要运行您的第一个脚本，请打开任意 SillyTavern 聊天，并在聊天输入栏中输入以下内容：

```stscript
/pass Hello, World! | /echo
```

| ![Hello World](/static/scripts/hello-world.png) |
|-------------------------------------------------|

您应该会在屏幕顶部的通知中看到该消息。现在我们逐步分解来看。

脚本是一批命令，每个命令以斜杠开头，可以带命名参数或未命名参数，并以命令分隔符 `|` 结尾。

命令按顺序依次执行，并在彼此之间传递数据。

1. `/pass` 命令接受一个常量值 "Hello, World!" 作为未命名参数，并将其写入管道。
2. `/echo` 命令通过管道从前一个命令接收值，并将其显示为通知消息。

> **💡 Tip**
>
> **提示：** 要查看所有可用命令的列表，请在聊天中输入 `/help slash`。


由于常量未命名参数和管道是可互换的，我们可以将这个脚本简单地改写为：

```stscript
/echo Hello, World!
```

## 用户输入

现在我们为脚本添加一点交互性。我们将接收来自用户的输入值，并将其显示在通知中。

```stscript
/input Enter your name |
/echo Hello, my name is {{pipe}}
```

1. `/input` 命令用于显示一个带有指定提示文本（未命名参数）的输入框，然后将输出写入管道。
2. 因为 `/echo` 已经有了设置输出模板的未命名参数，我们使用 `{{pipe}}` 宏来指定管道值渲染的位置。

| ![Slim Shady 输入](/static/scripts/slim-input.png) | ![Slim Shady 输出](/static/scripts/slim-output.png) |
|-----------------------------------------------------|-------------------------------------------------------|

### 其他输入/输出命令

- `/popup (text)` — 显示一个阻塞弹窗，支持轻量 HTML 格式化，例如：`/popup <font color=red>I'm red!</font>`。
- `/setinput (text)` — 用提供的文本替换用户输入栏的内容。
- `/speak voice="name" (text)` — 使用选定的 TTS 引擎和语音映射中的角色名称朗读文本，例如：`/speak name="Donald Duck" Quack!`。
- `/buttons labels=["a","b"] (text)` — 显示一个带有指定文本和按钮标签的阻塞弹窗。`labels` 必须是一个 JSON 序列化的字符串数组，或者一个包含此类数组的变量名。返回点击的按钮标签到管道，如果取消则返回空字符串。文本支持轻量 HTML 格式化。
- `/beep` — 播放消息通知音。

#### `/popup` 和 `/input` 的参数

`/popup` 和 `/input` 支持以下附加命名参数：
- `large=on/off` - 增加弹窗的垂直尺寸。默认：`off`。
- `wide=on/off` - 增加弹窗的水平尺寸。默认：`off`。
- `okButton=string` - 允许自定义“确定”按钮上的文本。默认：`Ok`。
- `rows=number` - (仅限 `/input`) 增加输入控件的尺寸。默认：1。
- `placeholder=string` - 设置输入字段中的占位符文本。
- `tooltip=string` - 设置悬停时显示的工具提示。
- `icon=string` - 设置弹窗的 Font Awesome 图标类。

示例：
```stscript
/popup large=on wide=on okButton="Accept" Please accept our terms and conditions....
```

#### `/echo` 的参数

`/echo` 支持以下附加参数 `severity` 的值，用于设置显示消息的样式。
  - `warning`
  - `error`
  - `info` (默认)
  - `success`

示例：

```stscript
/echo severity=error Something really bad happened.
```

## 变量

变量用于在脚本中存储和操作数据，可以使用命令或宏。变量可以是以下类型之一：

- 局部变量 — 保存到当前聊天元数据中，并对其唯一。
- 全局变量 — 保存到 settings.json 中，并在整个应用程序中存在。

1. `/getvar name` 或 `{{getvar::name}}` — 获取局部变量的值。
2. `/setvar key=name value` 或 `{{setvar::name::value}}` — 设置局部变量的值。
3. `/addvar key=name increment` 或 `{{addvar::name::increment}}` — 将 `increment` 加到局部变量的值上。
4. `/incvar name` 或 `{{incvar::name}}` — 将局部变量的值增加 1。
5. `/decvar name` 或 `{{decvar::name}}` — 将局部变量的值减少 1。
6. `/getglobalvar name` 或 `{{getglobalvar::name}}` — 获取全局变量的值。
7. `/setglobalvar key=name` 或 `{{setglobalvar::name::value}}` — 设置全局变量的值。
8. `/addglobalvar key=name` 或 `{{addglobalvar::name:increment}}` — 将 `increment` 加到全局变量的值上。
9. `/incglobalvar name` 或 `{{incglobalvar::name}}` — 将全局变量的值增加 1。
10. `/decglobalvar name` 或 `{{decglobalvar::name}}` — 将全局变量的值减少 1。
11. `/flushvar name` — 删除局部变量的值。
12. `/flushglobalvar name` — 删除全局变量的值。

- 先前未定义的变量的默认值是空字符串，或者如果首次在 `/addvar`、`/incvar`、`/decvar` 命令中使用，则为零。
- 在 `/addvar` 命令中，如果增量值和变量值都可以转换为数字，则执行加或减操作；否则执行字符串连接。
- 如果命令参数接受变量名，并且存在同名的局部变量和全局变量，则 *局部变量* 优先。
- 所有用于变量操作的 *斜杠命令* 都会将结果值写入管道，供下一个命令使用。
- 对于 *宏*，只有“get”、“inc”和“dec”类型的宏返回值，“add”和“set”则被替换为空字符串。

现在，考虑以下示例：

```stscript
/input What do you want to generate? |
/setvar key=SDinput |
/echo Requesting an image of {{getvar::SDinput}} |
/getvar SDinput |
/imagine
```

1. 用户输入的值保存在名为 `SDinput` 的局部变量中。
2. 使用 `getvar` 宏在 `/echo` 命令中显示该值。
3. 使用 `getvar` 命令检索变量的值并通过管道传递。
4. 该值被传递给 `/imagine` 命令（由图像生成插件提供）作为其输入提示。

由于变量在脚本执行之间保存且不会被清除，您可以在其他脚本中通过宏引用该变量，它将解析为与示例脚本执行期间相同的值。为了确保值被丢弃，请将 `/flushvar` 命令添加到脚本中。

### 数组和对象

变量值可以包含 JSON 序列化的数组或键值对（对象）。

示例：
- 数组：`["apple","banana","orange"]`
- 对象：`{"fruits":["apple","banana","orange"]}`

以下修改可以应用于命令以处理这些变量：

- `/len` 命令获取数组中的元素数量。
- 可以向 `/getvar` 或 `/setvar`（及其全局对应命令）添加 `index=number/string` 命名参数，以根据数组的零基索引或对象的字符串键获取或设置子值。
  - 如果对不存在的变量使用数字索引，则该变量将作为空数组 `[]` 创建。
  - 如果对不存在的变量使用字符串索引，则该变量将作为空对象 `{}` 创建。
- `/addvar` 和 `/addglobalvar` 命令支持向数组类型的变量推送新值。

## 流程控制——条件

您可以使用 `/if` 命令创建条件表达式，根据定义的规则分支执行。

```stscript
/if left=valueA right=valueB rule=comparison else={: /echo (command on false) :} {: /echo (command on true) :}
```

请注意，以下语法也支持：

```stscript
/if left=valueA right=valueB rule=comparison else="(command on false)" "(command on true)"
```

然而，使用 `{: 闭包 :}` 将帮助您编写更清晰的脚本。

让我们回顾以下示例：

```stscript
/input What's your favorite drink? |
/if left={{pipe}} right="black tea" rule=eq else={: /echo You shall not pass | /abort :} {: /echo Welcome to the club, {{user}} :}
```

该脚本根据用户输入与所需值进行比较，并根据输入值显示不同的消息。

### `/if` 的参数

1. `left` 是第一个操作数。我们称之为 A。
2. `right` 是第二个操作数。我们称之为 B。
3. `rule` 是要应用于操作数的操作。
4. `else` 是可选的子命令字符串，如果布尔比较结果为 false 时执行。
5. 未命名参数是在布尔比较结果为 true 时执行的子命令。

操作数的值按以下顺序计算：

1. 数字字面量
2. 局部变量名
3. 全局变量名
4. 字符串字面量

命名参数的字符串值可以用引号转义，以允许多词字符串。引号随后会被丢弃。

### 布尔运算

支持的布尔比较规则如下。应用于操作数的操作结果为 true 或 false。

1. `eq` (等于) => A = B
2. `neq` (不等于) => A != B
3. `lt` (小于) => A < B
4. `gt` (大于) => A > B
5. `lte` (小于等于) => A <= B
6. `gte` (大于等于) => A >= B
7. `not` (一元否定) => !A
8. `in` (包含子串) => A 包含 B，不区分大小写
9. `nin` (不包含子串) => A 不包含 B，不区分大小写

### 子命令

子命令是一个包含要执行的斜杠命令列表的字符串。

1. 要在子命令中使用命令批处理，命令分隔符字符应被转义（见下文）。
2. 由于宏值在进入条件时执行，而不是在子命令执行时执行，因此可以额外转义宏，以将其求值延迟到子命令执行时间。
3. 子命令执行的结果被管道传递到 `/if` 之后的命令。
4. `/abort` 命令在遇到时中断脚本执行。

`/if` 命令可以用作三元运算符。
以下示例将在变量 `a` 等于 5 时向下一个命令传递字符串 "true"，否则传递 "false"。

```stscript
/if left=a right=5 rule=eq else={: /pass false:} {: /pass true :} |
/echo
```

## 转义序列

### 宏

宏的转义方式与以前一样。但是，使用闭包时，您需要转义宏的频率将大大降低。可以转义开头两个大括号，或者同时转义开头和结尾的一对。

```stscript
/echo \{\{char}} |
/echo \{\{char\}\}
```

### 管道

在闭包中（当用作命令分隔符时），管道不需要转义。在您想要使用字面管道字符而不是命令分隔符的任何地方，都需要转义它。

```stscript
/echo title="a\|b" c\|d |
/echo title=a\|b c\|d |
```

使用解析器标志 `STRICT_ESCAPING` 时，您不需要转义引号值中的管道。

```stscript
/parser-flag STRICT_ESCAPING |
/echo title="a|b" c\|d |
/echo title=a\|b c\|d |
```

### 引号

要在引号值中使用字面引号字符，必须转义该字符。

```stscript
/echo title="a \"b\" c" d "e" f
```

### 空格

要在命名参数的值中使用空格，您必须用引号将值括起来，或者转义空格字符。

```stscript
/echo title="a b" c d |
/echo title=a\ b c d
```

### 闭包分隔符

如果您想使用用于标记闭包开始或结束的字符组合，则必须使用单个反斜杠转义该序列。

```stscript
/echo \{: |
/echo \:}
```

## 管道阻断器

```stscript
||
```

为防止前一个命令的输出自动作为未命名参数注入到下一个命令中，请在两个命令之间放置双管道。

```stscript
/echo we don't want to pass this on ||
/world
```

## 闭包

```stscript
{: ... :}
```

闭包（块语句、lambda、匿名函数，随便怎么称呼）是用 `{:` 和 `:}` 包裹的一系列命令，只有在代码执行到该部分时才会被求值。

### 子命令

闭包使得使用子命令变得容易得多，并消除了转义管道和宏的需要。

```stscript
// 不带闭包的 if |
/if left=1 rule=eq right=1
    else="
        /echo not equal \|
        /return 0
    "
    /echo equal \|
    /return \{\{pipe}}
```

```stscript
// 带闭包的 if |
/if left=1 rule=eq right=1
    else={:
        /echo not equal |
        /return 0
    :}
    {:
        /echo equal |
        /return {{pipe}}
    :}
```

### 作用域

闭包拥有自己的作用域，并支持作用域变量。作用域变量用 `/let` 声明，其值用 `/var` 设置和检索。另一种获取作用域变量的方法是使用 `{{var::}}` 宏。

```stscript
/let x |
/let y 2 |
/var x 1 |
/var y |
/echo x is {{var::x}} and y is {{pipe}}.
```

在闭包内，您可以访问在同一闭包或其祖先之一中声明的所有变量。您无法访问在闭包的后代中声明的变量。  
如果声明了一个与某个祖先闭包中声明的变量同名的变量，那么您将无法在此闭包及其后代中访问该祖先变量。

```stscript
/let x this is root x |
/let y this is root y |
/return {:
    /echo called from level-1: x is "{{var::x}}" and y is "{{var::y}}" |
    /delay 500 |
    /let x this is level-1 x |
    /echo called from level-1: x is "{{var::x}}" and y is "{{var::y}}" |
    /delay 500 |
    /return {:
        /echo called from level-2: x is "{{var::x}}" and y is "{{var::y}}" |
        /let x this is level-2 x |
        /echo called from level-2: x is "{{var::x}}" and y is "{{var::y}}" |
        /delay 500
    :}()
:}() |
/echo called from root: x is "{{var::x}}" and y is "{{var::y}}"
```

### 命名闭包

```stscript
/let x {: ... :} | /:x
```

闭包可以赋值给变量（仅限作用域变量），以便稍后调用或用作子命令。

```stscript
/let myClosure {:
    /echo this is my closure
:} |
/:myClosure
```

```stscript
/let myClosure {:
    /echo this is my closure |
    /delay 500
:} |
/times 3 {{var::myClosure}}
```

`/:` 也可以用于执行快速回复，因为它只是 `/run` 的简写。

```stscript
/:QrSetName.QrButtonLabel |
/run QrSetName.QrButtonLabel
```

### 闭包参数

命名闭包可以接受命名参数，就像斜杠命令一样。参数可以有默认值。

```stscript
/let myClosure {: a=1 b=
    /echo a is {{var::a}} and b is {{var::b}}
:} |
/:myClosure b=10
```

### 闭包和管道参数

来自父闭包的管道值不会自动注入到子闭包的第一个命令中。  
您仍然可以显式地使用 `{{pipe}}` 引用父级的管道值，但是如果您将闭包内第一个命令的未命名参数留空，则该值将 *不会* 被自动注入。

```stscript
/* 过去这会尝试将模型改为 "foo"
   因为循环外 /echo 中的值 "foo"
   被注入到循环内的 /model 命令中。
   现在它只会简单回显当前模型，而不会
   尝试更改它。
*|
/echo foo |
/times 2 {:
	/model |
	/echo |
:} |
```
```stscript
/* 您仍然可以通过显式使用 {{pipe}} 宏
   来重现旧的行为。
*|
/echo foo |
/times 2 {:
	/model {{pipe}} |
	/echo |
:} |
```

### 立即执行闭包

```stscript
{: ... :}()
```

闭包可以立即执行，这意味着它们将被替换为它们的返回值。这在没有闭包显式支持的地方很有用，并且可以缩短一些否则需要大量中间变量的命令。

```stscript
// 不带闭包的简单字符串长度比较 |
/len foo |
/var lenOfFoo {{pipe}} |
/len bar |
/var lenOfBar {{pipe}} |
/if left={{var::lenOfFoo}} rule=eq right={{var:lenOfBar}} /echo yay!
```

```stscript
// 使用立即执行闭包的相同比较 |
/if left={:/len foo:}() rule=eq right={:/len bar:}() /echo yay!
```

除了运行保存在作用域变量中的命名闭包外，`/run` 命令也可以用于立即执行闭包。

```stscript
/run {:
	/add 1 2 3 4 |
:} |
/echo |
```

## 注释

```stscript
// ... | /# ...
```

注释是脚本代码中人类可读的解释或注解。注释不会中断管道。

```stscript
// this is a comment |
/echo foo |
/# this is also a comment
```

### 块注释

块注释可用于快速注释掉多个命令。它们不会在管道处终止。

```stscript
/echo foo |
/*
/echo bar |
/echo foobar |
*|
/echo foo again |
```

## 流程控制

### 循环：`/while` 和 `/times`

如果您需要在满足某个条件之前循环运行某个命令，请使用 `/while` 命令。

```stscript
/while left=valueA right=valueB rule=operation guard=on "commands"
```

在循环的每一步，它比较变量 A 的值与变量 B 的值，如果条件为真，则执行引号中包含的任何有效斜杠命令，否则退出循环。此命令不向输出管道写入任何内容。

#### `/while` 的参数

**可用的布尔比较集、变量处理、字面值和子命令与 `/if` 命令相同。**

可选的 `guard` 命名参数（默认为 `on`）用于防止无限循环，将迭代次数限制为 100。
要禁用并允许无限循环，设置 `guard=off`。

此示例将 `i` 的值加 1，直到达到 10，然后输出结果值（本例中为 10）。

```stscript
/setvar key=i 0 |
/while left=i right=10 rule=lt "/addvar key=i 1" |
/echo {{getvar::i}} |
/flushvar i
```

#### `/times` 的参数

运行子命令指定次数。

`/times (repeats) "(command)"` – 引号中包含的任何有效斜杠命令重复指定次数，例如 `/setvar key=i 1 | /times 5 "/addvar key=i 1"` 将 "i" 的值加 1 五次。
- `{{timesIndex}}` 被替换为迭代编号（从零开始），例如 `/times 4 {:/echo {{timesIndex}}:}` 回显数字 0 到 4。
- 循环默认限制为 100 次迭代，传递 `guard=off` 可禁用。

### 跳出循环和闭包

```stscript
/break |
```

`/break` 命令可用于提前跳出循环（`/while` 或 `/times`）或闭包。`/break` 的未命名参数可用于传递与当前管道不同的值。  
`/break` 当前在以下命令中实现：
- `/while` - 提前退出循环
- `/times` - 提前退出循环
- `/run`（带闭包或通过变量的闭包） - 提前退出闭包
- `/:`（带闭包） - 提前退出闭包

```stscript
/times 10 {:
	/echo {{timesIndex}}
	/delay 500 |
	/if left={{timesIndex}} rule=gt right=3 {:
		/break
	:} |
:} |
```

```stscript
/let x {: iterations=2
	/if left={{var::iterations}} rule=gt right=10 {:
		/break too many iterations! |
	:} |
	/times {{var::iterations}} {:
		/delay 500 |
		/echo {{timesIndex}} |
	:} |
:} |
/:x iterations=30 |
/echo the final result is: {{pipe}}
```

```stscript
/run {:
	/break 1 |
	/pass 2 |
:} |
/echo pipe will be one: {{pipe}} |
```

```stscript
/let x {:
	/break 1 |
	/pass 2 |
:} |
/:x |
/echo pipe will be one: {{pipe}} |
```

## 数学运算

- 以下所有操作都接受一系列数字或变量名，并将结果输出到管道。
- 无效操作（如除以零）以及导致 NaN 值或无穷大的操作返回零。
- 乘法、加法、最小值和最大值接受数量不限的参数，用空格分隔。
- 减法、除法、乘方和取模接受两个参数，用空格分隔。
- 正弦、余弦、自然对数、平方根、绝对值和舍入接受一个参数。

**操作列表：**

1. `/add (a b c d)` – 对一组值执行加法，例如 `/add 10 i 30 j`
2. `/mul (a b c d)` – 对一组值执行乘法，例如 `/mul 10 i 30 j`
3. `/max (a b c d)` – 返回一组值中的最大值，例如 `/max 1 0 4 k`
4. `/min (a b c d)` – 返回一组值中的最小值，例如 `/min 5 4 i 2`
5. `/sub (a b)` – 对两个值执行减法，例如 `/sub i 5`
6. `/div (a b)` – 对两个值执行除法，例如 `/div 10 i`
7. `/mod (a b)` – 对两个值执行取模运算，例如 `/mod i 2`
8. `/pow (a b)` – 对两个值执行乘方运算，例如 `/pow i 2`
9. `/sin (a)` – 对一个值执行正弦运算，例如 `/sin i`
10. `/cos (a)` – 对一个值执行余弦运算，例如 `/cos i`
11. `/log (a)` – 对一个值执行自然对数运算，例如 `/log i`
12. `/abs (a)` – 对一个值执行绝对值运算，例如 `/abs -10`
13. `/sqrt (a)` – 对一个值执行平方根运算，例如 `/sqrt 9`
14. `/round (a)` – 对一个值执行四舍五入到最接近整数的运算，例如 `/round 3.14`
15. `/rand (round=round|ceil|floor from=number=0 to=number=1)` – 返回一个介于 from 和 to 之间的随机数，例如 `/rand` 或 `/rand 10` 或 `/rand from=5 to=10`。范围是包含的。返回值将包含小数部分。使用 `round` 命名参数获取整数值，例如 `/rand round=ceil` 向上取整，`round=floor` 向下取整，`round=round` 四舍五入。

### 示例 1：计算半径为 50 的圆的面积。

```stscript
/setglobalvar key=PI 3.1415 |
/setvar key=r 50 |
/mul r r PI |
/round |
/echo Circle area: {{pipe}}
```

### 示例 2：计算 5 的阶乘。

```stscript
/setvar key=input 5 |
/setvar key=i 1 |
/setvar key=product 1 |
/while left=i right=input rule=lte "/mul product i \| /setvar key=product \| /addvar key=i 1" |
/getvar product |
/echo Factorial of {{getvar::input}}: {{pipe}} |
/flushvar input |
/flushvar i |
/flushvar product
```

## 使用 LLM

脚本可以使用以下命令向您当前连接的 LLM API 发出请求：

- `/gen (prompt)` — 使用提供的提示词为选定角色生成文本，并包含聊天消息。
- `/genraw (prompt)` — 仅使用提供的提示词生成文本，忽略当前角色和聊天。
- `/trigger` — 触发正常生成（相当于点击“发送”按钮）。如果在群聊中，您可以可选地提供基于 1 的群成员索引或角色名称让其回复，否则根据群组设置触发群组轮次。
- `/swipe` — 触发对最后一条角色消息的滑动。
- `/regenerate` — 重新生成最后一条角色消息。
- `/continue` — 尝试继续最后一条消息。

### `/gen` 和 `/genraw` 的参数

```stscript
/genraw lock=on/off stop=[] instruct=on/off (prompt)
```

- `lock` — 可以是 `on` 或 `off`。指定生成过程中是否应阻止用户输入。默认：`off`。
- `stop` — JSON 序列化的字符串数组。仅为本次生成添加自定义停止字符串（如果 API 支持）。默认：无。
- `instruct`（仅 `/genraw`）— 可以是 `on` 或 `off`。允许对输入提示词使用指令格式化（如果启用指令模式且 API 支持）。设置为 `off` 以强制使用纯提示词。默认：`on`。
- `as`（对于文本补全 API）— 可以是 `system`（默认）或 `char`。定义最后一行提示词将如何格式化。`char` 将使用角色名称，`system` 将使用无名称或中性名称。

生成的文本随后通过管道传递给下一个命令，并可以使用 I/O 功能保存到变量或显示：

```stscript
/genraw Write a funny message from Cthulhu about taking over the world. Use emojis. |
/popup <h3>Cthulhu says:</h3><div>{{pipe}}</div>
```

| ![Cthulhu 说](/static/scripts/cthulhu-says.png) |
|---------------------------------------------------|

或插入生成的消息作为您的角色的回复：

```stscript
/genraw You have been memory wiped, your name is now Lisa and you're tearing me apart. You're tearing me apart Lisa! |
/sendas name={{char}} {{pipe}}
```

## 临时角色

如果您不在群聊中，脚本可以临时以不同角色向当前连接的 LLM 发出请求。

- `/ask (prompt)` — 使用提供的提示词为指定角色生成文本，并包含聊天消息。请注意，对该角色回复的滑动将恢复为当前角色。

```stscript
/ask name=... (prompt)
```
### `/ask` 的参数

- `name` — **必需**。要询问的角色名称（或唯一的角色标识符，例如头像键）。必须作为命名参数提供。
- `return` — 指定如何提供返回值。默认为 `pipe`（通过命令管道输出）。如果 API 支持，可以指定其他选项。


```stscript
/ask name=Alice What is your favorite color?
```

## 提示注入

脚本可以添加自定义 LLM 提示注入，这本质上相当于无限制的作者注释。

- `/inject (text)` — 将任意文本插入当前聊天的正常 LLM 提示词中，并需要唯一标识符。保存到聊天元数据。
- `/listinjects` — 以系统消息的形式显示当前聊天中由脚本添加的所有提示注入列表。
- `/flushinjects` — 删除当前聊天中由脚本添加的所有提示注入。
- `/note (text)` — 设置当前聊天的作者注释值。保存到聊天元数据。
- `/interval` — 设置当前聊天的作者注释插入间隔。
- `/depth` — 设置聊天内位置的作者注释插入深度。
- `/position` — 设置当前聊天的作者注释位置。

### `/inject` 的参数

```stscript
/inject id=IdGoesHere position=chat depth=4 My prompt injection
```

- `id` — 标识符字符串或对变量的引用。后续使用相同 ID 调用 `/inject` 将覆盖之前的文本注入。**必需参数。**
- `position` — 设置注入的位置。默认：`after`。可能的值：
  - `after`：主提示词之后。
  - `before`：主提示词之前。
  - `chat`：聊天内。
- `depth` — 设置聊天内位置的注入深度。0 表示插入到最后一条消息之后，1 - 最后一条消息之前，以此类推。默认：4。
- 未命名参数是要注入的文本。空字符串将取消设置提供的标识符的先前值。

## 访问聊天消息

### 读取消息

您可以使用 `/messages` 命令访问当前选定聊天中的消息。

```stscript
/messages names=on/off start-finish
```

- `names` 参数用于指定是否包含角色名称，默认：`on`。
- 在未命名参数中，它接受消息索引或 `start-finish` 格式的范围。范围是包含的！
- 如果范围无法满足，即索引无效或请求的消息超出存在数量，则返回空字符串。
- 从提示词中隐藏的消息（由幽灵图标表示）将从输出中排除。
- 如果您想知道最新消息的索引，请使用 `{{lastMessageId}}` 宏，而 `{{lastMessage}}` 将获取消息本身。

要计算范围的起始索引，例如当您需要获取最后 N 条消息时，请使用变量减法。
此示例将获取聊天中的最后 3 条消息：

```stscript
/setvar key=start {{lastMessageId}} |
/addvar key=start -2 |
/messages names=off {{getvar::start}}-{{lastMessageId}} |
/setinput
```

### 发送消息

脚本可以以用户、角色、身份、中性叙述者的身份发送消息，或添加注释。

1. `/send (text)` — 以当前选定的身份添加消息。
2. `/sendas name=charname (text)` — 以任何匹配其名称的角色添加消息。`name` 参数是必需的。使用 `{{char}}` 宏以当前角色发送。
3. `/sys (text)` — 添加一条来自中性叙述者的消息，该消息不属于用户或角色。显示的名称纯粹是装饰性的，可以使用 `/sysname` 命令自定义。
4. `/comment (text)` — 添加一条隐藏评论，该评论显示在聊天中，但对提示词不可见。
5. `/addswipe (text)` — 为最后一条角色消息添加滑动。无法为用户或隐藏消息添加滑动。
6. `/hide (message id or range)` — 根据提供的消息索引或 `start-finish` 格式的包含范围，从提示词中隐藏一条或多条消息。
7. `/unhide (message id or range)` — 根据提供的消息索引或 `start-finish` 格式的包含范围，将一条或多条消息恢复到提示词中。

`/send`、`/sendas`、`/sys` 和 `/comment` 命令可选地接受一个命名参数 `at`，其值为基于零的数字（或包含此类值的变量名），该参数指定消息插入的确切位置。默认情况下，新消息插入到聊天记录的末尾。

这将在对话历史的开头插入一条用户消息：

```stscript
/send at=0 Hi, I use Linux.
```

### 删除消息

**这些命令可能具有破坏性，没有“撤销”功能。如果您不小心删除了重要内容，请检查 /backups/ 文件夹。**

1. `/cut (message id or range)` — 根据提供的消息索引或 `start-finish` 格式的包含范围，从聊天中剪切一条或多条消息。
2. `/del (number)` — 从聊天中删除最后 N 条消息。
3. `/delswipe (1-based swipe id)` — 根据提供的基于 1 的滑动 ID，从最后一条角色消息中删除一个滑动。
4. `/delname (character name)` — 删除当前聊天中属于具有指定名称的角色所有消息。
5. `/delchat` — 删除当前聊天。

## 角色管理命令

1. `/char-create` — 使用命名参数提供的数据创建新角色。
2. `/char-update` — 使用命名参数提供的数据更新当前角色。
3. `/char-get` — 以 JSON 对象的形式检索当前角色的数据，并将其传递给管道。
4. `/char-delete (name)` — 删除具有指定名称的角色。
5. `/char-duplicate (name)` — 复制具有指定名称的角色。
6. `/tag-import (name)` — 从角色卡文件导入标签。

## 加载器命令

加载器系统为耗时任务提供可重用的覆盖层，应提供视觉反馈和/或临时阻止 UI。

1. `/loader-show (text)` — 显示带有指定文本的加载覆盖层。
2. `/loader-hide` — 隐藏加载覆盖层。
3. `/loader-wrap (closure)` — 显示加载覆盖层，执行提供的闭包，完成后隐藏覆盖层。
4. `/loader-stop` — 停止并移除加载覆盖层。

## 世界信息命令

世界信息（也称为 Lorebook）是一个高度实用的工具，用于动态插入数据到提示词中。有关更详细的说明，请参阅专门页面：[World Info](/usage/core-concepts/worldinfo/)。

1. `/getchatbook` – 获取聊天绑定的世界信息文件名，或者如果未绑定则创建一个新文件，并将其传递到管道。
2. `/findentry file=bookName field=fieldName [text]` – 通过使用模糊匹配将字段值与提供的文本（默认字段：`key`）进行比较，从指定文件（或指向文件名的变量）中找到记录的 UID，并将 UID 传递到管道，例如 `/findentry file=chatLore field=key Shadowfang`。
3. `/getentryfield file=bookName field=field [UID]` – 从指定的世界信息文件（或指向文件名的变量）中获取具有指定 UID 记录的字段值（默认字段：`content`），并将值传递到管道，例如 `/getentryfield file=chatLore field=content 123`。
4. `/setentryfield file=bookName uid=UID field=field [text]` – 从指定的世界信息文件（或指向文件名的变量）中设置具有指定 UID（或指向 U