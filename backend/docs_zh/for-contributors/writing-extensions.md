
# UI 扩展

UI 扩展通过挂接 SillyTavern 的事件和 API 来扩展其功能。它们在浏览器环境中运行，实际上可以不受限制地访问 DOM、JavaScript API 和 SillyTavern 上下文。扩展可以修改 UI、调用内部 API，并与聊天数据交互。本指南将解释如何创建你自己的扩展（需要具备 JavaScript 知识）。

> **💡 只是想安装扩展？**
>
> 请前往此处：[扩展](/extensions/)。


要扩展 Node.js 服务器的功能，请参阅[服务器插件](/for-contributors/server-plugins/)页面。

**不会写 JavaScript？**

* 可以考虑使用 [STscript](/usage/st-script/) 作为编写完整扩展的更简单替代方案。
* 学习 [MDN 课程](https://developer.mozilla.org/en-US/docs/Learn/JavaScript)，学完后再回来。

## 扩展提交

想将你的扩展贡献到[官方内容仓库](https://github.com/SillyTavern/SillyTavern-Content)？请联系我们！

为确保所有扩展安全且易于使用，我们有以下几点要求：

1. 你的扩展必须是开源的，并采用自由许可证（参见[选择许可证](https://choosealicense.com/licenses/)）。如果不确定，AGPLv3 是一个不错的选择。
2. 扩展必须与 SillyTavern 的最新发布版本兼容。如果核心部分发生变化，请准备好更新你的扩展。
3. 扩展必须有完善的文档。这包括一个 README 文件，其中包含安装说明、使用示例和功能列表。
4. 需要服务器插件才能运行的扩展将不被接受。

## 示例

查看简单的 SillyTavern 扩展示例：

* <https://github.com/city-unit/st-extension-example> - 基础扩展模板。展示了清单创建、本地脚本导入、添加设置 UI 面板以及持久化扩展设置的使用。
* <https://github.com/search?q=topic%3Aextension+org%3ASillyTavern&type=Repositories> - GitHub 上所有官方 SillyTavern 扩展的列表。

## 打包

扩展也可以利用打包技术将自己与其他模块隔离，并使用来自 NPM 的任何依赖项，包括 Vue、React 等 UI 框架。

* <https://github.com/SillyTavern/Extension-WebpackTemplate> - 使用 TypeScript 和 Webpack 的扩展模板仓库（不含 React）。
* <https://github.com/SillyTavern/Extension-ReactTemplate> - 使用 React 和 Webpack 的极简扩展模板仓库。

要从打包中使用相对导入，你可能需要创建一个导入包装器。以下是 Webpack 的示例：

```js
/**
 * 通过 URL 从模块导入成员，绕过 webpack。
 * @param {string} url 要导入的 URL
 * @param {string} what 要导入的成员名称
 * @param {any} defaultValue 回退值
 * @returns {Promise<any>} 导入的成员
 */
export async function importFromUrl(url, what, defaultValue = null) {
    try {
        const module = await import(/* webpackIgnore: true */ url);
        if (!Object.hasOwn(module, what)) {
            throw new Error(`No ${what} in module`);
        }
        return module[what];
    } catch (error) {
        console.error(`Failed to import ${what} from ${url}: ${error}`);
        return defaultValue;
     }
}

// 从 'script.js' 模块导入一个函数
const generateRaw = await importFromUrl('/script.js', 'generateRaw');
```

## manifest.json

每个扩展必须在 `data/<user-handle>/extensions` 中有一个文件夹，并包含一个 `manifest.json` 文件，其中包含有关扩展的元数据以及指向作为扩展入口点的 JS 脚本文件的路径。

可下载的扩展在通过 HTTP 提供服务时会被挂载到 `/scripts/extensions/third-party` 文件夹中，因此应基于该路径使用相对导入。为便于本地开发，请考虑将你的扩展仓库放在 `/scripts/extensions/third-party` 文件夹中（“为所有用户安装”选项）。

```json
{
    "display_name": "The name of the extension",
    "loading_order": 1,
    "requires": [],
    "optional": [],
    "dependencies": [],
    "js": "index.js",
    "css": "style.css",
    "author": "Your name",
    "version": "1.0.0",
    "homePage": "https://github.com/your/extension",
    "auto_update": true,
    "minimum_client_version": "1.0.0",
    "i18n": {
        "de-de": "i18n/de-de.json"
    },
    "hooks": {
        "install": "onInstall",
        "update": "onUpdate",
        "delete": "onDelete",
        "enable": "onEnable",
        "disable": "onDisable",
        "activate": "onActivate"
    }
}
```

### 清单字段

* `display_name` 是必需的。它显示在“管理扩展”菜单中。
* `loading_order` 是可选的。数字越大，加载越晚。
* `js` 是主 JS 文件引用，是必需的。
* `css` 是可选的样式文件引用。
* `author` 是必需的。它应包含作者的名称或联系信息。
* `auto_update` 如果扩展应在 ST 包版本更改时自动更新，则设置为 `true`。
* `i18n` 是一个可选对象，指定支持的语言区域及其对应的 JSON 文件（见下文）。
* `dependencies` 是一个可选字符串数组，指定此扩展依赖的其他**扩展**。
* `generate_interceptor` 是一个可选字符串，指定在文本生成请求时调用的全局函数名称。
* `minimum_client_version` 是一个可选字符串，指定此扩展正常工作所需的最低 SillyTavern 版本。
* `hooks` 是一个可选对象，指定从 JS 入口点模块导出的[生命周期钩子](#生命周期钩子)函数名称。

### 依赖项

扩展也可以依赖其他 SillyTavern 扩展。如果任何这些依赖项缺失或被禁用，扩展将不会加载。

依赖项通过其在 `public/extensions` 目录中显示的**文件夹名称**来指定。

示例：

* 内置扩展：`"vectors"`、`"caption"`
* 第三方扩展：`"third-party/Extension-WebLLM"`、`"third-party/Extension-Mermaid"`

### 已弃用字段

* `requires` 是一个可选字符串数组，指定所需的 **Extras 模块**。如果连接的 Extras API 未提供所有列出的模块，则扩展将不会加载。
* `optional` 是一个可选字符串数组，指定可选的 **Extras 模块**。如果这些模块缺失，扩展仍会加载，扩展应优雅地处理它们的缺失。

要检查连接的 Extras API 当前提供哪些模块，请从 `scripts/extensions.js` 导入 `modules` 数组。


## 脚本编写

### 扩展初始化的最佳实践

* 使用 `activate` 钩子进行需要在 SillyTavern 加载阶段（阻塞加载器处于活动状态时）运行的同步设置。
* 使用 `APP_INITIALIZED` 事件进行应在所有扩展和 UI 元素加载并设置完成后（但加载器仍在阻塞时）运行的设置。
* 使用 `APP_READY` 事件进行不需要阻止 SillyTavern 准备就绪的异步设置。它应使用计时器或类似机制来延迟处理，因为事件处理程序将被等待。

### 使用 getContext

`SillyTavern` 全局对象中的 `getContext()` 函数让你可以访问 SillyTavern 上下文，它是所有主应用状态对象、有用函数和实用工具的集合。

```js
const context = SillyTavern.getContext();
context.chat; // 聊天记录 - 可变
context.characters; // 角色列表
context.characterId; // 当前角色的索引
context.groups; // 群组列表
context.groupId; // 当前群组的 ID
// 以及更多...
```

你可以在 [SillyTavern 源代码](https://github.com/SillyTavern/SillyTavern/blob/staging/public/scripts/st-context.js)中找到可用属性和函数的完整列表。

> **📝 提示**
如果你在 `getContext` 中缺少任何函数/属性，请联系开发者或向我们发送拉取请求！
> **📝 提示**

### 共享库

SillyTavern 前端内部使用的大多数 npm 库都共享在 `SillyTavern` 全局对象的 `libs` 属性中。

* `lodash` - 实用工具库。[文档](https://lodash.com/)。
* `Fuse` - 模糊搜索库。[文档](https://www.fusejs.io/)。
* `DOMPurify` - HTML 清理库。[文档](https://github.com/cure53/DOMPurify)。
* `hljs` - 语法高亮库。[文档](https://highlightjs.org/)。
* `localforage` - 浏览器存储库（IndexedDB/localStorage 抽象）。[文档](https://localforage.github.io/localForage/)。
* `Handlebars` - 模板库。[文档](https://handlebarsjs.com/)。
* `css` - CSS 解析/字符串化工具。[文档](https://github.com/nicolo-ribaudo/css-tools)。
* `Bowser` - 浏览器/平台检测库。[文档](https://github.com/bowser-js/bowser)。
* `DiffMatchPatch` - 文本差异、匹配和补丁库。[文档](https://github.com/google/diff-match-patch)。
* `Readability` / `isProbablyReaderable` - Mozilla 的文章提取库。[文档](https://github.com/mozilla/readability)。
* `SVGInject` - 内联 SVG 注入库。[文档](https://github.com/nicolo-ribaudo/svg-inject)。
* `showdown` - Markdown 转换器库。[文档](https://showdownjs.com/)。
* `moment` - 日期/时间操作库。[文档](http://momentjs.com/)。
* `seedrandom` - 种子随机数生成器。[文档](https://github.com/davidbau/seedrandom)。
* `Popper` - 工具提示/弹出框定位引擎。[文档](https://popper.js.org/)。
* `droll` - 骰子滚动库。[文档](https://github.com/thebinarypenguin/droll)。
* `morphdom` - 快速 DOM 差异/补丁库。[文档](https://github.com/patrick-steele-iber/morphdom)。
* `slideToggle` - 原生 JS 滑动切换动画。[文档](https://github.com/nicolo-ribaudo/slidetoggle)。
* `chalk` - 终端字符串样式（浏览器中用途有限）。[文档](https://github.com/chalk/chalk)。
* `yaml` - YAML 解析器和字符串化器。[文档](https://eemeli.org/yaml/)。
* `chevrotain` - 解析器构建工具包。[文档](https://chevrotain.io/)。
* `gzipSync` / `gzip` - 来自 fflate 的快速压缩实用工具。[文档](https://github.com/101arrowz/fflate)。

你可以在 [SillyTavern 源代码](https://github.com/SillyTavern/SillyTavern/blob/staging/public/lib.js)中找到导出库的完整列表。

**示例：** 使用 DOMPurify 库。

```js
const { DOMPurify } = SillyTavern.libs;

const sanitizedHtml = DOMPurify.sanitize('<script>"dirty HTML"</script>');
```

### TypeScript 注意事项

如果你想为 `SillyTavern` 全局对象中的所有方法（你可能确实需要）获得自动补全，包括 `getContext()` 和 `libs`，你应该添加一个 TypeScript `.d.ts` 模块声明。此声明应根据你的扩展位置从 SillyTavern 源代码导入全局类型。以下是一个适用于两种安装类型（“所有用户”和“当前用户”）的示例。

**global.d.ts** - 将此文件放在扩展目录的根目录中（与 `manifest.json` 相邻）：

```ts
export {};

// 1. 用户范围扩展的导入
import '../../../../public/global';
// 2. 服务器范围扩展的导入
import '../../../../global';

// 如果需要，定义其他类型...
declare global {
    // 在此处添加全局类型声明
}
```

### HTML 模板

扩展可以使用 Handlebars HTML 模板来构建其 UI。将 `.html` 模板文件放在扩展目录中，并使用 `getContext()` 中的 `renderExtensionTemplateAsync()` 函数渲染它们。

该函数接受扩展的文件夹名称、模板文件名（不带 `.html`）以及可选的 Handlebars 模板变量数据对象。返回的 HTML 会自动使用 DOMPurify 清理，并使用 `data-i18n` 属性进行本地化。

```js
const { renderExtensionTemplateAsync } = SillyTavern.getContext();

// 使用给定数据渲染 'third-party/my-extension/settings.html'
const settingsHtml = await renderExtensionTemplateAsync(
    'third-party/my-extension',
    'settings',
    { title: 'My Extension', version: '1.0', defaultValue: 'test' }
);

// 追加到扩展设置面板
$('#extensions_settings2').append(settingsHtml);
```

**模板文件示例**（`settings.html`）：

```html
<div class="my-extension-settings">
    <div class="inline-drawer">
        <div class="inline-drawer-toggle inline-drawer-header">
            <b data-i18n="{{title}}">{{title}}</b>
            <div class="inline-drawer-icon fa-solid fa-circle-chevron-down down"></div>
        </div>
        <div class="inline-drawer-content">
            <label for="my_ext_option">
                <span data-i18n="Option">Option</span>
            </label>
            <input id="my_ext_option" type="text" value="{{defaultValue}}" />
        </div>
    </div>
</div>
```

> **⚠️ Warning**
>
> `renderExtensionTemplate()`（同步）已弃用。请始终使用 `renderExtensionTemplateAsync()` 代替。


### 从其他文件导入

> **⚠️ Warning**
>
> 使用来自 SillyTavern 代码的导入是不可靠的，如果 ST 模块的内部结构发生变化，随时可能中断。`getContext` 提供了更稳定的 API。


除非你正在构建打包扩展，否则你可以从其他 JS 文件导入变量和函数。

例如，以下代码片段将在后台从当前选定的 API 生成回复：

```js
import { generateQuietPrompt } from "../../../../script.js";

async function handleMessage(data) {
    const text = data.message;
    const translated = await generateQuietPrompt({ quietPrompt: text });
    // ...
}
```

## 状态管理

### 持久化设置

当扩展需要持久化其状态时，它可以使用 `getContext()` 函数中的 `extensionSettings` 对象来存储和检索数据。扩展可以在设置对象中存储任何可 JSON 序列化的数据，并且必须使用唯一的键以避免与其他扩展冲突。

要持久化设置，请使用 `saveSettingsDebounced()` 函数，它会将设置保存到服务器。

```js
const { extensionSettings, saveSettingsDebounced } = SillyTavern.getContext();

// 为你的扩展定义一个唯一标识符
const MODULE_NAME = 'my_extension';

// 定义默认设置
const defaultSettings = Object.freeze({
    enabled: false,
    option1: 'default',
    option2: 5
});

// 定义一个获取或初始化设置的函数
function getSettings() {
    // 如果设置不存在则初始化
    if (!extensionSettings[MODULE_NAME]) {
        extensionSettings[MODULE_NAME] = structuredClone(defaultSettings);
    }

    // 确保所有默认键都存在（在更新后很有用）
    for (const key of Object.keys(defaultSettings)) {
        if (!Object.hasOwn(extensionSettings[MODULE_NAME], key)) {
            extensionSettings[MODULE_NAME][key] = defaultSettings[key];
        }
    }

    return extensionSettings[MODULE_NAME];
}

// 使用设置
const settings = getSettings();
settings.option1 = 'new value';

// 保存设置
saveSettingsDebounced();
```

### 聊天元数据

要将某些数据绑定到特定聊天，你可以使用 `getContext()` 函数中的 `chatMetadata` 对象。此对象允许你存储与聊天关联的任意数据，这对于存储扩展特定的状态很有用。

要持久化元数据，请使用 `saveMetadata()` 函数，它会将元数据保存到服务器。

> **⚠️ Warning**
>
> 不要将 `chatMetadata` 的引用保存在长期变量中，因为当切换聊天时引用会改变。请始终使用 `SillyTavern.getContext().chatMetadata` 来访问当前聊天元数据。


```js
const { chatMetadata, saveMetadata } = SillyTavern.getContext();

// 为当前聊天设置一些元数据
chatMetadata['my_key'] = 'my_value';

// 获取当前聊天的元数据
const value = chatMetadata['my_key'];

// 将元数据保存到服务器
await saveMetadata();
```

> **💡 Tip**
>
> 当切换聊天时会发出 `CHAT_CHANGED` 事件，因此你可以监听此事件以相应地更新扩展的状态。更多信息请参阅[监听事件](#监听事件)部分。


### 角色卡

SillyTavern 完全支持[角色卡 V2 规范](https://github.com/malfoyslastname/character-card-spec-v2/blob/main/spec_v2.md)，它允许在角色卡 JSON 数据中存储任意数据。

这对于需要存储与角色关联的附加数据并在导出角色卡时使其可共享的扩展很有用。

要将数据写入角色卡[扩展](https://github.com/malfoyslastname/character-card-spec-v2/blob/main/spec_v2.md#extensions)数据字段，请使用 `getContext()` 函数中的 `writeExtensionField` 函数。此函数接受角色 ID、字符串键和要写入的值。值必须是可 JSON 序列化的。

> **⚠️ 前方有奇怪之处**
>
> 尽管被称为 `characterId`，但它不是“真正的”唯一标识符，而是 `characters` 数组中角色的索引。
>
> 当前角色的索引由上下文中的 `characterId` 属性提供。如果你想将数据写入当前选定的角色，请使用 `SillyTavern.getContext().characterId`。如果你需要为另一个角色存储数据，请通过在 `characters` 数组中搜索该角色来找到索引。
>
> **注意：在群聊中或未选择角色时，`characterId` 为 `undefined`！**


```js
const { writeExtensionField, characterId } = SillyTavern.getContext();

// 将一些数据写入角色卡
await writeExtensionField(characterId, 'my_extension_key', {
    someData: 'value',
    anotherData: 42
});

// 从角色卡读回数据
const character = SillyTavern.getContext().characters[characterId];
// 数据存储在角色数据的 `extensions` 对象中
const myData = character.data?.extensions?.my_extension_key;
```

### 设置预设

任意 JSON 数据可以存储在主 API 类型的设置预设中。它将随预设 JSON 一起导出和导入，因此你可以使用它为预设存储扩展特定的设置。以下 API 类型支持设置预设中的数据扩展：

* 聊天补全
* 文本补全
* NovelAI
* KoboldAI / AI Horde

要读取或写入数据，你首先需要从上下文获取 PresetManager 实例：

```js
const { getPresetManager } = SillyTavern.getContext();

// 获取当前 API 类型的预设管理器
const pm = getPresetManager();

// 将数据写入预设扩展字段：
// - path：预设数据中字段的路径
// - value：要写入的值
// - name（可选）：要写入的预设名称，默认为当前选定的预设
await pm.writePresetExtensionField({ path: 'hello', value: 'world' });

// 从预设扩展字段读取数据：
// - path：预设数据中字段的路径
// - name（可选）：要读取的预设名称，默认为当前选定的预设
const value = pm.readPresetExtensionField({ path: 'hello' });
```

> **💡 Tip**
>
> 当预设更改或主 API 切换时会发出 `PRESET_CHANGED` 和 `MAIN_API_CHANGED` 事件，因此你可以监听这些事件以相应地更新扩展的状态。更多信息请参阅[监听事件](#监听事件)部分。


## 国际化

> **📝 提示**
有关提供翻译的一般信息，请参阅[国际化](/for-contributors/i18n/)页面。
> **📝 提示**

扩展可以为 `t`、`translate` 函数以及 HTML 模板中的 `data-i18n` 属性提供额外的本地化字符串。

在此处查看支持的语言区域列表（`lang` 键）：<https://github.com/SillyTavern/SillyTavern/blob/release/public/locales/lang.json>

### 直接调用 `addLocaleData`

将语言区域代码和包含翻译的对象传递给 `addLocaleData` 函数。*不*允许覆盖现有键。如果传入的语言区域代码不是当前选定的语言区域，数据将被静默忽略。

```js
SillyTavern.getContext().addLocaleData('fr-fr', { 'Hello': 'Bonjour' });
SillyTavern.getContext().addLocaleData('de-de', { 'Hello': 'Hallo' });
```

### 通过扩展清单

在清单中添加一个 i18n 对象，其中包含支持的语言区域列表及其对应的 JSON 文件路径（相对于扩展目录）。

```json
{
  "display_name": "Foobar",
  "js": "index.js",
  // 其余字段
  "i18n": {
    "fr-fr": "i18n/french.json",
    "de-de": "i18n/german.json"
  }
}
```

## 注册斜杠命令（新方式）

虽然 `registerSlashCommand` 仍然存在以保持向后兼容性，但新的斜杠命令现在应通过 `SlashCommandParser.addCommandObject()` 注册，以向解析器（进而向自动补全和命令帮助）提供有关命令及其参数的扩展详细信息。

```javascript
SlashCommandParser.addCommandObject(SlashCommand.fromProps({ name: 'repeat',
    callback: (namedArgs, unnamedArgs) => {
        return Array(namedArgs.times ?? 5)
            .fill(unnamedArgs.toString())
            .join(isTrueBoolean(namedArgs.space.toString()) ? ' ' : '')
        ;
    },
    aliases: ['example-command'],
    returns: 'the repeated text',
    namedArgumentList: [
        SlashCommandNamedArgument.fromProps({ name: 'times',
            description: 'number of times to repeat the text',
            typeList: ARGUMENT_TYPE.NUMBER,
            defaultValue: '5',
        }),
        SlashCommandNamedArgument.fromProps({ name: 'space',
            description: 'whether to separate the texts with a space',
            typeList: ARGUMENT_TYPE.BOOLEAN,
            defaultValue: 'off',
            enumList: ['on', 'off'],
        }),
    ],
    unnamedArgumentList: [
        SlashCommandArgument.fromProps({ description: 'the text to repeat',
            typeList: ARGUMENT_TYPE.STRING,
            isRequired: true,
        }),
    ],
    helpString: `
        <div>
            Repeats the provided text a number of times.
        </div>
        <div>
            <strong>Example:</strong>
            <ul>
                <li>
                    <pre><code class="language-stscript">/repeat foo</code></pre>
                    returns "foofoofoofoofoo"
                </li>
                <li>
                    <pre><code class="language-stscript">/repeat times=3 space=on bar</code></pre>
                    returns "bar bar bar"
                </li>
            </ul>
        </div>
    `,
}));
```

所有注册的命令都可以以任何可能的方式在 [STscript](/usage/st-script/) 中使用。

## 事件

### 监听事件

使用 `eventSource.on(eventType, eventHandler)` 监听事件：

```js
const { eventSource, event_types } = SillyTavern.getContext();

eventSource.on(event_types.MESSAGE_RECEIVED, handleIncomingMessage);

function handleIncomingMessage(data) {
    // 处理消息
}
```

主要事件类型有：

**应用生命周期：**

* `APP_INITIALIZED`：应用已初始化并接近就绪，但加载器仍然可见。可以在此处进行 UI 修改。在应用初始化后，每次附加新监听器时都会自动触发。
* `APP_READY`：应用已完全加载并准备就绪。在应用就绪后，每次附加新监听器时都会自动触发。

**消息：**

* `MESSAGE_SENT`：消息由用户发送并记录到 `chat` 对象中，但尚未在 UI 中渲染。
* `MESSAGE_RECEIVED`：LLM 消息已生成并记录到 `chat` 对象中，但尚未在 UI 中渲染。
* `USER_MESSAGE_RENDERED`：用户发送的消息已在 UI 中渲染。
* `CHARACTER_MESSAGE_RENDERED`：生成的 LLM 消息已在 UI 中渲染。
* `MESSAGE_EDITED`：消息已被用户编辑。
* `MESSAGE_DELETED`：消息已被删除。
* `MESSAGE_SWIPED`：已触发消息滑动。
* `STREAM_TOKEN_RECEIVED`：在流式生成期间接收到新令牌。

**生成：**

* `GENERATION_AFTER_COMMANDS`：在处理斜杠命令后，生成即将开始。
* `GENERATION_STARTED`：生成已开始。
* `GENERATION_STOPPED`：生成已被用户停止。
* `GENERATION_ENDED`：生成已完成或已出错。

**聊天：**

* `CHAT_CHANGED`：聊天已切换（例如，切换到另一个角色，或加载了另一个聊天）。
* `CHAT_CREATED`：已创建新聊天。
* `CHAT_DELETED`：聊天已被删除。

**角色：**

* `CHARACTER_EDITED`：角色的数据已更改。
* `CHARACTER_DELETED`：角色已被删除。
* `CHARACTER_DUPLICATED`：角色已被复制。

**人设：**

* `PERSONA_CHANGED`：活动人设已更改。
* `PERSONA_CREATED`：已创建新人设。
* `PERSONA_UPDATED`：人设已更新。
* `PERSONA_RENAMED`：人设已重命名。
* `PERSONA_DELETED`：人设已被删除。

**设置和预设：**

* `SETTINGS_UPDATED`：应用程序设置已更新。
* `PRESET_CHANGED`：活动预设已更改。
* `MAIN_API_CHANGED`：主 API 类型已切换。
* `CHATCOMPLETION_SOURCE_CHANGED`：聊天补全源已更改。
* `CHATCOMPLETION_MODEL_CHANGED`：聊天补全模型已更改。
* `CONNECTION_PROFILE_LOADED`：连接配置文件已加载。

**世界信息：**

* `WORLDINFO_UPDATED`：世界信息数据已更新。
* `WORLDINFO_SETTINGS_UPDATED`：世界信息设置已更改。

**工具调用：**

* `TOOL_CALLS_PERFORMED`：工具调用已执行。
* `TOOL_CALLS_RENDERED`：工具调用结果已在聊天中渲染。

**文本转语音：**

* `TTS_JOB_STARTED`：TTS 任务已开始。
* `TTS_AUDIO_READY`：TTS 音频数据已准备好播放。
* `TTS_JOB_COMPLETE`：TTS 任务已完成。

事件类型的完整列表可以在[源代码](https://github.com/SillyTavern/SillyTavern/blob/staging/public/scripts/events.js)中找到。

> **ℹ️ 事件数据**
>
> 每个事件将数据传递给监听器的方式并不统一。有些事件不发出任何数据；有些传递对象或原始值。请参阅发出事件的源代码以查看它传递的数据，或使用调试器检查。


### 发出事件

你可以通过调用 `eventSource.emit(eventType, ...eventData)` 从扩展产生任何应用程序事件，包括自定义事件：

```js
const { eventSource } = SillyTavern.getContext();

// 可以是内置的 event_types 字段或任何字符串。
const eventType = 'myCustomEvent';

// 使用 `await` 确保所有事件处理程序在继续执行之前完成。
await eventSource.emit(eventType, { data: 'custom event data' });
```

## 提示拦截器

提示拦截器为扩展提供了一种方式，可以在发出文本生成请求之前执行任何活动，例如修改聊天数据、添加注入或中止生成。

来自不同扩展的拦截器按顺序运行。顺序由各自 `manifest.json` 文件中的 `loading_order` 字段决定。`loading_order` 值较低的扩展先运行。如果未指定 `loading_order`，则使用 `display_name` 作为回退。如果两者都未指定，则顺序未定义。

### 注册拦截器

要定义提示拦截器，请在你的扩展的 `manifest.json` 文件中添加 `generate_interceptor` 字段。该值应为将由 SillyTavern 调用的全局函数的名称。

```json
{
    "display_name": "My Interceptor Extension",
    "loading_order": 10, // 影响执行顺序
    "generate_interceptor": "myCustomInterceptorFunction",
    // ... 其他清单属性
}
```

### 拦截器函数

`generate_interceptor` 函数是一个全局函数，将在非试运行的生成请求时被调用。它必须在全局作用域中定义（例如 `globalThis.myCustomInterceptorFunction = async function(...) { ... }`），并且如果需要执行任何异步操作，可以返回一个 `Promise`。

拦截器函数接收以下参数：

* `chat`：表示将用于提示构建的聊天历史的消息对象数组。你可以直接修改此数组（例如添加、删除或更改消息）。请注意，消息是可变的，因此你对数组所做的任何更改都将反映在实际的聊天历史中。如果你希望更改是临时的，请使用 `structuredClone` 创建消息对象的深拷贝。
* `contextSize`：一个数字，表示为即将进行的生成计算的当前上下文大小（以令牌为单位）。
* `abort`：一个函数，调用时将发出信号以阻止文本生成继续进行。它接受一个布尔参数，如果为 `true`，则阻止任何后续拦截器运行。
* `type`：一个字符串，表示生成的类型或触发方式（例如 `'quiet'`、`'regenerate'`、`'impersonate'`、`'swipe'` 等）。这有助于拦截器根据生成的启动方式有条件地应用逻辑。

**示例实现：**

```javascript
globalThis.myCustomInterceptorFunction = async function(chat, contextSize, abort, type) {
    // 示例：在最后一条用户消息之前添加系统注释
    const systemNote = {
        is_user: false,
        name: "System Note",
        send_date: Date.now(),
        mes: "This was added by my extension!"
    };
    // 插入到最后一条消息之前
    chat.splice(chat.length - 1, 0, systemNote);
}
```

## 生命周期钩子

扩展可以在 `manifest.json` 中定义生命周期钩子，这些钩子在扩展生命周期的特定点被调用。每个钩子映射到扩展 JS 入口点模块（`js` 字段中指定的文件）中的**导出函数**。

所有钩子都是可选的。钩子函数可以返回一个将被等待的 `Promise`（有 5 秒超时）。如果钩子超过超时时间，将记录警告并继续执行。钩子中的错误会被捕获并记录，不会阻止操作。

### 可用钩子

| 钩子 | 调用时机 |
|------|-----------------|
| `activate` | 当扩展在页面加载期间成功激活时 |
| `install` | 在扩展安装并加载其设置后 |
| `update` | 在成功更新扩展后（在重新加载提示之前） |
| `delete` | 在从服务器删除扩展之前 |
| `enable` | 在启用扩展并保存设置之前 |
| `disable` | 在禁用扩展并保存设置之前 |
| `clean` | 当用户在扩展管理器中点击“清理扩展数据”按钮，或在删除扩展时选择清理选项时 |

### 清单配置

在你的 `manifest.json` 中添加一个 `hooks` 对象，将钩子名称映射到导出函数名称：

```json
{
    "display_name": "My Extension",
    "js": "index.js",
    // 其他字段...
    "hooks": {
        "install": "onInstall",
        "update": "onUpdate",
        "delete": "onDelete",
        "enable": "onEnable",
        "disable": "onDisable",
        "activate": "onActivate",
        "clean": "onClean"
    }
}
```

名称可以自由选择，只要它们是有效的 JS 函数名称即可。  
可以配置任意数量的钩子，你不必填写和实现所有钩子。

### 实现

从你的主 JS 入口点导出钩子函数。每个函数不接收参数，并且可以选择性地返回一个 `Promise`：

```js
// index.js - 你的扩展的入口点

export async function onInstall() {
    console.log('Extension installed! Performing first-time setup...');
    // 例如，初始化默认数据、创建存储条目
}

export async function onActivate() {
    console.log('Extension activated during page load');
}

export async function onUpdate() {
    console.log('Extension updated! Running migrations...');
    // 例如，将数据从旧格式迁移到新格式
}

export async function onDelete() {
    console.log('Extension about to be deleted. Cleaning up...');
    // 例如，删除存储的数据、清理 localStorage
    const { localforage } = SillyTavern.libs;
    await localforage.removeItem('my_extension_data');
}

export function onEnable() {
    console.log('Extension enabled');
}

export function onDisable() {
    console.log('Extension disabled');
}

export async function onClean() {
    console.log('Extension data cleaned');
    // 例如，在此处清理扩展的数据
}
```

> **⚠️ Warning**
>
> 钩子函数有 **5 秒超时**。如果你的钩子耗时更长，执行将继续并记录警告。保持钩子逻辑快速轻量。


## 生成文本

SillyTavern 提供了几个函数，使用当前选定的 LLM API 在不同上下文中生成文本。这些函数允许你在聊天上下文中生成文本、无任何上下文的原始生成，或使用结构化输出。

### 在聊天上下文中

`generateQuietPrompt()` 函数用于在聊天上下文中生成文本，并在后台添加一个“quiet”提示（历史后指令）（输出不会在 UI 中渲染）。这对于在不中断用户体验的同时保持相关聊天和角色数据完整的情况下生成文本很有用，例如生成摘要或图像提示。

```js
const { generateQuietPrompt } = SillyTavern.getContext();

const quietPrompt = 'Generate a summary of the chat history.';

const result = await generateQuietPrompt({
    quietPrompt,
});
```

### 原始生成

`generateRaw()` 函数用于在没有任何聊天上下文的情况下生成文本。当你想要完全控制提示构建过程时，它很有用。

它接受一个 `prompt` 作为文本补全字符串或聊天补全对象数组，根据选定的 API 类型使用适当的格式构建请求，例如在聊天/文本模式之间转换、应用指令格式等。你还可以向函数传递额外的 `systemPrompt` 和 `prefill`，以更好地控制生成过程。

```js
const { generateRaw } = SillyTavern.getContext();

const systemPrompt = 'You are a helpful assistant.';
const prompt = 'Generate a story about a brave knight.';
const prefill = 'Once upon a time,';

/*
在聊天补全模式下，将产生如下提示：
[
  {role: 'system', content: 'You are a helpful assistant.'},
  {role: 'user', content: 'Generate a story about a brave knight.'},
  {role: 'assistant', content: 'Once upon a time,'}
]
*/

/*
在文本补全模式下（无指令），将产生如下提示：
"You are a helpful assistant.\nGenerate a story about a brave knight.\nOnce upon a time,"
*/

const result = await generateRaw({
    systemPrompt,
    prompt,
    prefill,
});
```

### 结构化输出

> **ℹ️ Info**
>
> 目前仅由聊天补全 API 支持。可用性因所选源和模型而异。如果所选模型不支持结构化输出，生成将失败或返回空对象（`'{}'`）。请查看你正在使用的特定 API 的文档，以了解是否支持结构化输出。


你可以使用结构化输出功能来确保模型生成符合提供的 [JSON Schema](https://json-schema.org/learn) 的有效 JSON 对象。这对于需要结构化数据的扩展很有用，例如状态跟踪、数据分类等。

要使用结构化输出，你必须向 `generateRaw()` 或 `generateQuietPrompt()` 传递一个 JSON schema 对象。然后模型将生成与 schema 匹配的响应