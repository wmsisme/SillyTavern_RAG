
# 如何更新 Node.js

出于安全性和性能原因，保持 Node.js 运行时的最新状态非常重要。以下是针对不同操作系统更新 Node.js 的步骤。

我们建议使用最新的长期支持（LTS）版本，你可以在 [Node.js 官方网站](https://nodejs.org/en/about/previous-releases) 上找到。

## 如何检查当前的 Node.js 版本

1. 打开终端或命令提示符。
2. 输入以下命令并按回车：

```bash
node -v
```

## nvm（Node 版本管理器）——跨平台

如果你正在使用 `nvm`：

1. 打开终端。
2. 输入以下命令：

[**Unix/Linux/macOS：**](https://github.com/nvm-sh/nvm)

```bash
nvm install --lts
nvm use --lts
```

[**Windows：**](https://github.com/coreybutler/nvm-windows)

```bash
nvm install lts
nvm use lts
```

## Windows——常规安装

1. 前往 Node.js [下载页面](https://nodejs.org/en/download/)。
2. 下载 LTS 版本的 Windows 安装程序。
3. 运行安装程序，按照提示完成安装。

## Windows——SillyTavern Launcher

如果你已通过 SillyTavern Launcher 安装：

1. 打开 SillyTavern Launcher。
2. 导航至 `Toolbox / App Installer / Core Utilities / Install Node.js`。

**或者：**

在 PowerShell 中手动使用 winget：

```powershell
winget install --id=OpenJS.NodeJS.LTS  -e
```

## Android——Termux

1. 打开 Termux 应用。
2. 输入以下命令：

```bash
pkg update
pkg upgrade nodejs-lts
```

如果在更新过程中出现任何提示，别忘了在虚拟键盘上按 `Y` 键接受。

## macOS——常规安装

1. 前往 Node.js [下载页面](https://nodejs.org/en/download/)。
2. 下载 LTS 版本的 macOS 安装程序。
3. 运行 `.pkg` 文件，按照提示完成安装。

## macOS——Homebrew

如果你已安装 Homebrew，可以使用以下命令更新 Node.js：

```bash
brew update
brew upgrade node
```

## Linux——包管理器

在 Linux 上更新 Node.js 的方法取决于你的发行版。

但由于官方仓库中的 Node.js 版本可能不是最新的，我们建议使用 [Node 版本管理器（nvm）](https://github.com/nvm-sh/nvm) 或 [NodeSource 仓库](https://github.com/nodesource/distributions)。

## Docker

无需操作。我们提供的预构建 Docker 镜像已使用最新版本的 Node.js 编译。