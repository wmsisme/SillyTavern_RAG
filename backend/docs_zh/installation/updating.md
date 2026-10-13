
# 如何更新 SillyTavern

在下方找到你的操作系统，并按照说明更新 ST。

> **📝 安装说明请参阅 [安装](/installation/) 页面。**
>
>
> 本指南假设你已经至少安装并运行过一次 SillyTavern。


----

## Linux/Termux 或 MacOS

你肯定是通过 git 安装的，因此在 SillyTavern 目录内执行 `git pull` 即可。

- `cd SillyTavern` 进入正确的文件夹。
- `git pull` 获取更新。
- `./start.sh` 或 `bash start.sh` 启动 ST。

----

## Windows

>首先尝试使用 SillyTavern 安装根目录中的 `UpdateAndStart.bat`。

如果失败，请返回此处继续阅读。

### 方法 1 - GIT

我们始终建议用户使用 'git' 进行安装。原因如下：

当你通过 `git clone` 安装后，只需在 ST 文件夹的[命令行](https://www.google.com/search?q=how+to+open+command+prompt+in+a+folder)中输入 `git pull` 即可更新。
或者，如果命令行出现问题（且你已安装 GitHub Desktop），可以使用 `Repository` 菜单并选择 `Pull`。

更新会自动安全地应用。

#### "我最初是通过 Zip 安装的，现在想转换为 Git 安装"

你选择了一条明智的道路。

由于你是通过 Zip 安装的，你需要使用 git 进行全新安装。

幸运的是，我们有相关[说明](/installation/windows/)。

当你使用 git 将新的 SillyTavern 安装到**不同**文件夹后，请返回本页面并继续执行下方 'Zip 更新' 说明中的**步骤 4**。

### 方法 2 - ZIP

如果你坚持通过 zip 安装，以下是执行更新的繁琐过程：

1. 下载新的发布版 zip 文件。
2. 将其解压到当前 ST 安装目录**之外**的文件夹中。
3. 按照操作系统的常规设置流程安装 NodeJS 依赖。

4. 根据需要(*)从旧的 ST 安装中复制以下文件/文件夹：

    (*) '根据需要' = "如果你对这些文件夹做过任何自定义内容"。
    
    #### 从 >=1.12.0 更新
    
    将 `/data` 目录和 `config.yaml` 文件从一个安装复制到另一个安装。如果你有想要保留的服务器范围扩展（为"所有用户"安装），同时复制 `/public/scripts/extensions/third-party` 目录。
    
    #### 从 <1.12.0 更新到 >1.12.0
    
    1.12.0 包含自动迁移流程。仅当迁移中断或出错时，才需要执行以下步骤。

5. 至少运行一次更新后的服务器安装，以创建 `/data/default-user` 目录。
6. 根据需要将文件从旧的 `/public` 转移到新的 `/data/default-user`。
    
    没有必需的文件夹，因此只复制你需要的即可。
    
    **注意：不要复制整个 /public/ 文件夹**
    
    这样做可能会破坏新安装，并导致新功能无法使用。
    
    ```plaintext
    Assets
    Backgrounds
    Characters
    Chats
    Context
    Groups
    Group chats
    Instruct
    movingUI
    KoboldAI Settings
    NovelAI Settings
    OpenAI Settings
    QuickReplies
    TextGen Settings (textgen = ooba)
    Themes
    User Avatars
    Worlds
    User
    settings.json
    secrets.json <---- 此文件位于根文件夹，不在 /public/ 下
    ```

7. 复制完这些文件夹/文件后，将它们粘贴到新安装的 /data/default-user 文件夹中（secrets.json 放入文件夹根目录）。
8. 使用适合你操作系统的方法再次启动 SillyTavern，并祈祷一切正确。
9. 如果所有内容都正常显示，你可以安全地删除旧的 ST 文件夹。

### 常见更新问题

#### "工作目录中存在未解决的冲突。"

这意味着你修改了远程仓库中已更改的默认文件（例如设置预设）。

要解决此问题，请在终端中运行以下命令。请谨慎使用，因为它可能具有破坏性。如有需要，请确保已备份。

```bash
git merge --abort
git reset --hard
git pull --rebase --autostash
```

#### 文件更改阻止了 git pull

- 如果你更改了 SillyTavern 系统文件，`git pull` 可能无法正常工作。
- 有时更新可能需要我们更改一个重要文件，这可能导致同样的问题。
- 通常这是预设文件或 `package-lock.json`。
- 在这种情况下，你可以尝试将文件移动到其他文件夹（或删除文件），然后执行 `git pull`。
- 另一种解决方法是使用 `git pull --rebase --autostash`

#### 启动服务器时出现错误：找不到模块 "***"

- 这意味着 SillyTavern 添加了新的 npm 包依赖。
- 在 SillyTavern 目录中运行 `npm install` 以解决此问题。提供的 Start.bat 和 start.sh 脚本会自动执行此操作。
- 仍未解决？删除 node_modules 文件夹

**Windows**

```bash
rmdir /s /q node_modules
npm cache clean --force
npm install
```

**Unix/Linux**

```bash
rm -rf node_modules
npm cache clean --force
npm install
```

## Docker

1. 打开终端窗口，导航到你的 docker 目录 `cd SillyTavern/docker`
2. 使用 `docker compose down` 删除你的容器
3. 从缓存中删除 SillyTavern docker 镜像 `docker rmi ghcr.io/sillytavern/sillytavern:latest`（如果你目标是 staging 分支，将 `sillytavern:latest` 替换为 `sillytavern:staging`）
4. 使用 `sudo docker compose up -d` 重新构建容器

如果一切顺利，docker 应该开始重新下载镜像，你很快就能正常运行。如果遇到任何问题，请参考本指南的下一节。

### 常见更新问题
#### 我使用 Docker，更新后所有数据都丢失了！

你必须按照 [Docker 容器迁移指南](/installation/st-1.12.0-migration-guide/#containerized-docker-installs) 更新卷映射，以适应 1.12.0 中引入的新数据模型。

#### 运行 docker 命令时权限被拒绝

这是一个 Linux 问题，意味着你的权限设置不正确。有两种解决方法：

1. **简单方法**：如果你的用户具有 sudo 访问权限，只需在命令前加上 `sudo`（例如：`sudo docker compose down`）
2. **正确方法**：修复你的权限。这取决于你使用的 Linux 版本。网上有很多指南可以帮助你解决此问题。