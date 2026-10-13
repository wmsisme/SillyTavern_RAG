
多用户模式允许多人使用同一个 SillyTavern 服务器。每个用户拥有自己的设置、扩展和数据。用户账户可以设置密码保护。

> **⚠️ Warning**
>
> 用户密码仅能为多用户设置下的用户之间提供基本的隐私保护。它们并非安全功能，也不应被视为安全措施。所有用户数据（包括聊天历史、API 密钥及其他敏感信息）均以明文形式存储在服务器上。任何能够访问服务器文件系统的人都可以查看和修改这些数据。**请勿将 SillyTavern 用于公共服务器或与不受信任的用户共享。**


## 配置

要启用并使用多用户模式，请编辑 `config.yaml` 文件：

```yaml
# Enable multi-user mode
enableUserAccounts: true
# Enable discreet login mode: hides user list on the login screen
enableDiscreetLogin: true
```

1. 当用户账户设置被禁用时，会使用一个 `default-user` 回退管理员账户来存储用户数据。
2. 当谨慎登录设置被禁用时，登录屏幕会显示活动用户列表。如果启用，用户必须手动输入其手柄。

> **ℹ️ Info**
>
> 你无法从用户列表中**删除** `default-user` 账户，因为当 `enableUserAccounts` 设置为 `false` 时，它用于提供用户数据。但你可以**禁用**它以将其从列表中隐藏并禁止登录。


## 用户手柄

手柄是用户的唯一标识符。它只能由小写字母、数字和短横线组成。

用户数据目录的路径遵循以下模式：`%DATA_ROOT%/%USER_HANDLE%`。

有效用户手柄示例：

- default-user
- juan555
- flux-the-cat
- cool-guy1337

## 角色

- **管理员** - 可以管理（创建、删除、修改）其他用户。可以为所有用户安装扩展。
- **用户** - 无法管理其他用户。只能为自己安装扩展。

除拥有管理员面板访问权限外，两种用户角色在功能上完全相同，都可以无限制地使用 SillyTavern 的全部功能。用户权限的实现待定。

所有用户账户最初创建时均为普通用户，如有需要可提升为管理员。

### 登录屏幕

在此处可选择要使用的用户账户。根据 `enableDiscreetLogin` 配置值有两种样式。

当只有一个活动用户且该用户未设置密码时，登录屏幕会被跳过且不显示。

### 用户资料

你可以通过顶部菜单栏“用户设置”面板下的“账户”按钮访问账户自我管理菜单。

1. 显示名称 - 用于登录屏幕，可修改。与角色卡无关，且对 AI API 不可见——你仍可按需使用任意数量的角色卡。
2. 个人资料图片 - 用于登录屏幕。可以使用自定义图片、默认角色卡图片（若已设置），否则使用上次使用的角色卡图片。
3. 密码 - 锁图标反映账户保护状态（开锁 = 无密码）。可通过“更改密码”按钮设置、修改或删除密码。
4. 设置快照 - 访问并审查 `settings.json` 文件的备份，可创建或恢复快照。
5. 下载备份 - 下载用户数据文件夹的存档。
6. 重置设置 - 恢复出厂默认设置，同时保留其他数据（角色卡、聊天记录）。

## 密码恢复

1. 可通过登录屏幕恢复密码。你需要访问服务器控制台以获取一次性恢复码（由 4 位数字组成）。
2. 或者，你可以使用 SillyTavern 服务器中的实用脚本，通过提供用户手柄来重置密码。

```txt
用法：node recover.js [账户] [密码]
示例：node recover.js admin SecurePassword
```

## 内容脚手架

要为用户添加自定义内容，你可以使用内容脚手架功能。此功能允许你定义一组文件，这些文件会在服务器启动时复制到每个用户的数据目录中。

你必须为使用此功能在 `/default/scaffold` 目录中创建一个 `index.json` 文件。其语法与默认内容相同。所有文件路径应相对于 `/default/scaffold` 目录，你可以使用子目录来组织文件。

脚手架文件会在默认文件之前复制，这意味着它们会覆盖任何同名默认文件（预设/设置等）。

> **💡 Tip**
>
> 每个用户数据目录中都有一个 `content.log` 文件，列出了从脚手架和默认目录复制的所有文件。删除此文件可强制服务器在下次重启时重新同步内容。


### 识别的内容类型

| 类型                          | 值                    |
|-------------------------------|----------------------|
| settings.json                 | `'settings'`         |
| 角色卡                        | `'character'`        |
| 角色精灵                      | `'sprites'`          |
| 背景图片                      | `'background'`       |
| 世界信息文件                  | `'world'`            |
| 角色头像                      | `'avatar'`           |
| UI 主题                       | `'theme'`            |
| ComfyUI 工作流                | `'workflow'`         |
| KoboldAI Classic 预设         | `'kobold_preset'`    |
| 聊天补全预设                  | `'openai_preset'`    |
| NovelAI 预设                  | `'novel_preset'`     |
| 文本补全预设                  | `'textgen_preset'`   |
| 指令模式模板                  | `'instruct'`         |
| 上下文格式化模板              | `'context'`          |
| MovingUI 预设                 | `'moving_ui'`        |
| 快速回复集                    | `'quick_replies'`    |
| 系统提示模板                  | `'sysprompt'`        |
| 推理格式化模板                | `'reasoning'`        |

### 示例 (`/default/scaffold/index.json`)

```json
[
    {
        "filename": "themes/Midnight.json",
        "type": "theme"
    },
    {
        "filename": "backgrounds/city.png",
        "type": "background"
    },
    {
        "filename": "characters/Charlie.png",
        "type": "character"
    }
]
```