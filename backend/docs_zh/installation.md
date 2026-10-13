
# 安装

请按照您平台的安装指南操作：

*   [Windows](/installation/windows/)
*   [Linux 和 Mac](/installation/linuxmacos/)
*   [Android](/installation/android-(termux)/)
*   [Docker](/installation/docker/)

## 分支

SillyTavern 采用双分支系统进行开发，以确保所有用户都能获得流畅的体验。

*   `release` - 🌟 **推荐给大多数用户。** 这是最稳定且推荐的版本，仅在发布重大更新时才会更新，适用于大多数用户。通常每月更新一次。
*   `staging` - ⚠️ **不推荐随意使用。** 此分支包含最新功能，但请注意它可能随时出现问题。仅适用于高级用户和爱好者。每天更新数次。

## 全局 / 独立模式

SillyTavern 有两种运行模式，它们在配置和数据路径的处理方式上有所不同。

*   **独立模式（默认）** - 使用服务器目录中的 `config.yaml` 文件和 `data` 目录。所有数据将限定在安装路径内。这是推荐给大多数用户的模式。
*   **全局模式** - 使用系统范围的配置和数据路径。当您将 SillyTavern 作为包安装，或希望在多个安装之间共享相同的配置和数据时，此模式非常有用。

> **ℹ️ Info**
>
> 通过使用 [官方 npm 包](https://www.npmjs.com/package/sillytavern)（例如 `npx sillytavern@latest`）进行的安装将默认以全局模式运行。


### 数据路径

**独立模式**的路径是相对于 SillyTavern 安装目录的：

*   **配置路径**：`./config.yaml`
*   **数据根目录**：`./data/`

**全局模式**的路径依赖于操作系统：

*   **Linux**：`~/.local/share/SillyTavern/config.yaml`（或 `$XDG_DATA_HOME/SillyTavern/config.yaml`）和 `~/.local/share/SillyTavern/data/`（或 `$XDG_DATA_HOME/SillyTavern/data/`）
*   **Windows**：`%APPDATA%\SillyTavern\config.yaml` 和 `%APPDATA%\SillyTavern\data\`
*   **MacOS**：`~/Library/Application Support/SillyTavern/config.yaml` 和 `~/Library/Application Support/SillyTavern/data/`

### 如何以全局模式运行

> **⚠️ Warning**
>
> 在全局模式下运行时，`dataRoot` 和 `configPath` 不能通过 [CLI 参数](/administration/config-yaml/#command-line-arguments) 或 [config.yaml](/administration/config-yaml/) 进行覆盖。


1.  将 `--global` 参数传递给服务器启动命令（例如 `node server.js --global`）。
2.  将 `--global` 参数传递给 shell 启动脚本（例如 `Start.bat --global` 或 `./start.sh --global`）。
3.  使用 `package.json` 文件中的 `start:global` 脚本（例如 `npm run start:global`）。