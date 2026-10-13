
# Android (Termux) 安装

使用 Termux 可以在 Android 设备上原生运行 SillyTavern。

## 安装 Termux

> **💡 Tip**
>
> 请避免从 Google Play 商店安装 Termux，该版本已不再维护。
> 请改用 F-Droid（推荐）或 GitHub 发布版获取最新版本。


1. 从 [F-Droid](https://f-droid.org/en/packages/com.termux/) 或 [GitHub 发布版](https://github.com/termux/termux-app/releases) 下载 Termux。
2. 安装下载的 APK 文件。
3. 打开 Termux 并运行第一条命令：

   ```bash
   termux-change-repo
   ```

4. 选择“镜像组”并选择离你最近的服务器。你可以触摸屏幕或使用 [Unexpected Keyboard](https://play.google.com/store/apps/details?id=juloo.keyboard2&hl=en) 的手势操作。
5. 更新 Termux：

   ```bash
   pkg update && pkg upgrade
   ```

## 安装依赖

安装所需的软件包：

```bash
pkg install git nodejs-lts nano
```

> **⚠️ Warning**
>
> 如果你运行的是 32 位 Android，请参阅下面的[常见错误](#常见错误)部分以了解额外步骤。


## 安装 SillyTavern

克隆 SillyTavern 仓库（[如何选择分支](/installation/#分支)）：

- **发布分支：**

    ```bash
    git clone https://github.com/SillyTavern/SillyTavern -b release
    ```

- **测试分支：**

    ```bash
    git clone https://github.com/SillyTavern/SillyTavern -b staging
    ```

## 运行 SillyTavern

要运行 SillyTavern，请进入克隆的目录并运行启动脚本：

```bash
cd ~/SillyTavern
bash start.sh
```

要更新 SillyTavern，请进入 SillyTavern 目录并运行：

```bash
cd ~/SillyTavern
git pull --rebase --autostash
```

请参阅下面的[别名](#可选创建别名)部分，了解创建快捷方式以简化此过程的方法。

## 常见错误

### 不支持的平台：android arm LEtime-web

32 位 Android 需要外部依赖项，无法通过 npm 安装。

请使用以下命令安装：

```bash
pkg install esbuild
```

然后继续执行上面的安装步骤。

### 性能调优

> **ℹ️ Info**
>
> 有关提升性能的通用提示，请参阅相应的[常见问题部分](/usage/faq/#性能提示)。


由于 Android 设备的硬件限制，你可能需要调整以下 SillyTavern [config.yaml](/administration/config-yaml/) 设置，以优化内存、存储和 CPU 使用：

```yaml
performance:
  # 避免在需要之前加载所有角色数据
  lazyLoadCharacters: true
  # 禁用磁盘缓存以减少存储使用
  useDiskCache: false
backups:
  chat:
    # 可选：禁用自动聊天备份以节省存储空间
    enabled: false
```

> **💡 Tip**
>
> 使用 Termux 自带的 `nano` 文本编辑器编辑 `config.yaml` 文件：`nano ~/SillyTavern/config.yaml`


## 可选：创建别名

你可以为常用命令创建快捷方式，以简化工作流程。

1. 打开编辑器以修改 `.bashrc` 文件：

   ```bash
   nano ~/.bashrc
   ```

2. 添加以下行以创建别名：

   ```bash
   # 更新 Termux 软件包
   alias pkgup="pkg update && pkg upgrade"
   # 启动 SillyTavern
   alias st='cd ~/SillyTavern && bash start.sh'
   # 更新 SillyTavern
   alias stup='cd ~/SillyTavern && git pull --rebase --autostash'
   ```

3. 保存文件并退出编辑器（在 nano 中，按 `CTRL + X`，然后按 `Y`，最后按 `Enter`）。

4. 要应用更改，请运行：

   ```bash
   source ~/.bashrc
   ```

现在你可以使用以下命令：

- `st` 启动 SillyTavern
- `stup` 更新 SillyTavern
- `pkgup` 更新 Termux 软件包

## 延伸阅读

> **ℹ️ Info**
>
> 下面链接的指南并非由 SillyTavern 团队维护。


- ArroganceComplex#2659 编写的 Termux 中 SillyTavern 指南：<https://rentry.org/STAI-Termux>
- 使用 Material Files 访问 Termux 文件：<https://www.learntermux.tech/2020/10/Termux-File-Manager.html>
- 防止 Termux 进程深度休眠：<https://wiki.termux.com/wiki/Termux-wake-lock>