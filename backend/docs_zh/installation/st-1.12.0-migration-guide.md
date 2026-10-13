
# 1.12.0 迁移指南

SillyTavern 1.12.0（代号“Neo Server”更新）包含若干关键性变更，可能影响您使用 SillyTavern 的方式。

本指南将帮助您为更新做好准备，并提供进一步指导。

## 数据存储更新

1.12.0 更改了 SillyTavern 处理用户数据的方式。

此前，所有持久化数据都与前端部分一起存储在 `/public` 目录中，这造成了混乱和潜在的故障点，并且使容器化及系统级应用安装变得相当困难。

### 变更内容

`/public` 中所有持久化信息（完整列表见下方），如设置和聊天记录，已被移到一个可配置路径的独立目录中，使其可移植且独立于 Web 服务器本身。在需要兼容性时（例如托管扩展、完整尺寸角色卡片、用户图片上传等），已设置智能重定向以自动从数据目录托管用户文件。

### 设置数据根目录

您可以通过 `config.yaml` 或在启动服务器时使用 `--dataRoot` 控制台参数，提供数据根目录的绝对路径或相对（相对于 ST 仓库目录）路径。

> YAML 示例

```yaml
# -- 数据配置 --
# 用户数据存储的根目录
dataRoot: C:\Users\Harry\Documents\ST-Data
```

> 控制台示例

```bash
node server.js --dataRoot="/Users/harry/ST-Data"
# 或者
npm run start -- --dataRoot="/Users/harry/ST-Data"
```

默认的数据根目录路径为 `./data`，即 SillyTavern 仓库中的 `data` 目录。

> **ℹ️ 注意**
>
> 数据根目录路径应为 **完整绝对路径** 或 **完整相对路径**。您 _不能_ 使用路径快捷方式如 `~` 或 `%APP_DATA%`，因为这些由 shell 解析，而非操作系统。


### 迁移

#### **重要！** 开始之前

1. **仅当您希望将 dataRoot 移出默认位置时，才需执行此步骤。否则请跳过此部分。** 在拉取更新后首次运行服务器 _之前_ 设置数据根目录。运行 `npm install` 以让 `config.yaml` 填充新值，或传递控制台参数。
2. 所有数据将迁移到 `default-user` 账户中。更多信息请参见下方[用户](#users)部分。

#### 非容器化（裸机）安装

您无需做任何操作！当您启动 ST 服务器并检测到旧存储格式（通过检查 `/public/characters` 目录是否存在）时，自动迁移会为您处理一切。

移动任何文件时，将在 `/backups/_migration/YYYY-MM-DD`（解析为当前日期）目录中创建自动备份，但在运行迁移前进行完整手动备份始终是良好实践。

#### 容器化（Docker）安装

在 Docker 卷中迁移数据稍显复杂，但相当直接。虽然仓库提供的 `docker-compose.yml` 已更新以反映这些变更，但您可能需要调整自定义工作流程/部署。

**步骤 1.** 创建一个新卷，并将其挂载到容器内的 "/home/node/app/data" 路径。不要移除 `config` 卷。

```yaml
volumes:
    - "./config:/home/node/app/config"
    - "./data:/home/node/app/data"
```

**步骤 2.** 将 `config` 卷中除 `config.yaml` 文件之外的所有内容移动到 `data` 卷的 `default-user` 子目录中。

**步骤 3.** 重新构建容器并启动它。

> **ℹ️ 注意**
>
> `/public` 目录与 `config` 卷之间的软链接不再需要，也不再内置到 Docker 容器中！


#### 需要迁移的内容？

以下文件和目录需要进行数据迁移。假设使用默认配置，迁移前后的路径如下表所示。

| 迁移前                                 | 迁移后                                |
|----------------------------------------|--------------------------------------|
| /secrets.json                          | /data/default-user/secrets.json      |
| /thumbnails                            | /data/default-user/thumbnails        |
| /vectors                               | /data/default-user/vectors           |
| /public/settings.json                  | /data/default-user/settings.json     |
| /public/stats.json                     | /data/default-user/stats.json        |
| /public/assets                         | /data/default-user/assets            |
| /public/backgrounds                    | /data/default-user/backgrounds       |
| /public/characters                     | /data/default-user/characters        |
| /public/chats                          | /data/default-user/chats             |
| /public/context                        | /data/default-user/context           |
| /public/scripts/extensions/third-party | /data/default-user/extensions        |
| /public/group chats                    | /data/default-user/group chats       |
| /public/groups                         | /data/default-user/groups            |
| /public/instruct                       | /data/default-user/instruct          |
| /public/KoboldAI Settings              | /data/default-user/KoboldAI Settings |
| /public/movingUI                       | /data/default-user/movingUI          |
| /public/NovelAI Settings               | /data/default-user/NovelAI Settings  |
| /public/OpenAI Settings                | /data/default-user/OpenAI Settings   |
| /public/QuickReplies                   | /data/default-user/QuickReplies      |
| /public/TextGen Settings               | /data/default-user/TextGen Settings  |
| /public/themes                         | /data/default-user/themes            |
| /public/worlds                         | /data/default-user/worlds            |
| /default/content/content.log           | /data/default-user/content.log       |

## 用户

1.12.0 增加了（完全可选的）在同一服务器上创建多用户设置的能力，允许多个用户（甚至同时）使用各自完全隔离的 SillyTavern 实例。用户账户还可以设置密码保护，以提供额外的隐私层。

更多信息请参阅[用户](/administration/multi-user/)文档。