
# 服务器插件

这些插件可用于添加仅靠UI扩展无法实现的功能，例如创建新的API端点或使用浏览器环境中不可用的Node.JS包。

插件存放在SillyTavern的`plugins`目录中，并在服务器启动时加载，但*仅当*`config.yaml`文件中的`enableServerPlugins`设置为`true`时才会加载。

> **⚠️ 警告**
>
> **服务器插件未进行沙盒化。这意味着它们可能获得对整个文件系统的访问权限，或以普通UI扩展无法做到的方式引入广泛的安全漏洞。请仅安装来自您信任的开发者的服务器插件！**


所有官方服务器插件的列表，请参见GitHub组织页面：<https://github.com/search?q=topic%3Aplugin+org%3ASillyTavern&type=Repositories>

## 插件类型

### 文件

一个可执行的JavaScript文件，扩展名为".js"（用于CommonJS模块）或".mjs"（用于ES模块），其中包含一个导出`init`函数的模块。该函数接受一个Express路由器（专门为您的插件创建）作为参数，并返回一个Promise。

模块还应导出一个`info`对象，包含关于插件的描述信息（`id`、`name`和`description`字符串）。这将向加载器提供有关插件的信息。

您可以通过路由器注册路由，这些路由将注册在`/api/plugins/{id}/{route}`路径下。例如，`router.get('/foo')`对于`example`插件将产生如下路由：`/api/plugins/example/foo`。

插件还可以*可选地*导出一个`exit`函数，用于在关闭服务器时执行清理操作。它应没有参数，并必须返回一个Promise。

插件导出的TypeScript契约：

```ts
interface PluginInfo {
    id: string;
    name: string;
    description: string;
}

interface Plugin {
    init: (router: Router) => Promise<void>;
    exit: () => Promise<void>;
    info: PluginInfo;
}
```

以下是一个"Hello world!"插件的示例：

```js
/**
 * Initialize plugin.
 * @param {import('express').Router} router Express router
 * @returns {Promise<any>} Promise that resolves when plugin is initialized
 */
async function init(router) {
    // Do initialization here...
    router.get('/foo', req, res, function () {
       res.send('bar');
    });
    console.log('Example plugin loaded!');
    return Promise.resolve();
}

async function exit() {
    // Do some clean-up here...
    return Promise.resolve();
}

module.exports = {
    init,
    exit,
    info: {
        id: 'example',
        name: 'Example',
        description: 'My cool plugin!',
    },
};
```

### 目录

您可以通过以下方式之一（按优先级顺序）从`plugins`目录下的子目录加载插件：

1. 一个`package.json`文件，其中包含指向"main"字段中可执行文件的路径。
2. 用于CommonJS模块的`index.js`文件。
3. 用于ES模块的`index.mjs`文件。

生成的文件必须导出一个`init`函数和一个`info`对象，其要求与单个文件相同。

目录插件示例（包含一个`index.js`文件）：<https://github.com/SillyTavern/SillyTavern-DiscordRichPresence-Server>

### 打包

建议使用打包工具（如Webpack或Browserify）将所有依赖打包到一个文件中。请确保将"Node"设置为构建目标。

使用Webpack和TypeScript的插件模板仓库：<https://github.com/SillyTavern/Plugin-WebpackTemplate>