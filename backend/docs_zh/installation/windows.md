# Windows 安装

> **⚠️ Warning**
>
> 不要安装到任何 Windows 受控文件夹（Program Files、System32 等）。
>
> 不要以管理员权限运行 Start.bat。
>
> 无法在 Windows 7 上安装，因为它无法运行 NodeJS 20。


## 通过 Git 安装

1. 安装 [NodeJS](https://nodejs.org/en)（建议使用最新的 LTS 版本）。
2. 安装 [Git for Windows](https://gitforwindows.org/)。
3. 打开 Windows 资源管理器（`Win+E`）。
4. 浏览到或创建一个不受 Windows 控制或监视的文件夹（例如：`C:\MySpecialFolder\`）。
5. 通过点击顶部“地址栏”，输入 `cmd` 并按下 Enter，在该文件夹内打开命令提示符。
6. 当黑色窗口（命令提示符）弹出后，在其中输入以下命令之一并按下 Enter：

   - 稳定版分支：`git clone https://github.com/SillyTavern/SillyTavern -b release`
   - 测试版分支：`git clone https://github.com/SillyTavern/SillyTavern -b staging`

7. 克隆完成后，双击 `Start.bat` 让 NodeJS 安装所需的依赖。
8. 随后服务器将启动，SillyTavern 将在你的浏览器中打开。

## 通过 SillyTavern Launcher 安装

1. 在键盘上按 **`WINDOWS + R`** 打开运行对话框。然后运行以下命令安装 git：
   ```shell
   cmd /c winget install -e --id Git.Git
   ```
2. 在键盘上按 **`WINDOWS + E`** 打开文件资源管理器，导航到要安装启动器的文件夹。进入目标文件夹后，在地址栏输入 `cmd` 并按 Enter。然后运行以下命令：
   ```shell
   git clone https://github.com/SillyTavern/SillyTavern-Launcher.git && cd SillyTavern-Launcher && start installer.bat
   ```

## 通过 GitHub Desktop 安装
（此方法**仅**允许在 GitHub Desktop 中使用 git，如果也想在命令行使用 `git`，还需要安装 [Git for Windows](https://gitforwindows.org/)）

1. 安装 [NodeJS](https://nodejs.org/en)（建议使用最新的 LTS 版本）。
2. 安装 [GitHub Desktop](https://central.github.com/deployments/desktop/desktop/latest/win32)。
3. 安装 GitHub Desktop 后，点击 `Clone a repository from the internet...`（注意：此步骤**无需**创建 GitHub 账户）。

   ![image](/static/windows-1.png)

4. 在菜单中点击 URL 选项卡，输入此 URL `https://github.com/SillyTavern/SillyTavern`，然后点击 Clone。你可以更改本地路径来调整 SillyTavern 的下载位置。

   ![image](/static/windows-2.png)

5. 要打开 SillyTavern，请使用 Windows 资源管理器浏览到克隆仓库的文件夹。默认情况下，仓库会被克隆到：`C:\Users\你的 Windows 用户名\Documents\GitHub\SillyTavern`。

6. 双击 `start.bat` 文件。（注意：文件名中的 `.bat` 部分可能被操作系统隐藏，此时它看起来像一个名为“Start”的文件。双击它即可运行 SillyTavern）

   ![image](/static/windows-3.png)

7. 双击后，应出现一个黑色命令控制台窗口，SillyTavern 将开始安装其运行所需的内容。

8. 安装过程结束后，如果一切正常，命令控制台窗口应显示如下内容，并且浏览器中应打开一个 SillyTavern 标签页：

   ![image](/static/windows-4.png)

9. 连接到任意 [支持的 API](/usage/api-connections/) 并开始聊天！