
# 1.9.0 迁移指南

## 如果使用 main/dev 分支，如何迁移到新分支？

_**建议全新安装。**_ 不过，如果你希望使用现有的 SillyTavern 副本，请按照以下说明操作。

**重要！** 在执行任何操作之前，请对你的安装目录进行*完整备份*。在此过程中你可能会*丢失数据*，因此不要忽略此警告。

不确定要备份哪些文件？请参阅此处列表：[如何更新 SillyTavern](/installation/updating/#updating-from-1120-to-1120)

### git 安装

1. 在 SillyTavern 安装文件夹中打开终端提示符（cmd、PowerShell、Termux 等）。
2. 输入 `git fetch`，然后输入 `git pull` 以拉取更新。
3. 你可能会丢失设置。你是否已进行备份？`git switch release` 或 `git switch staging` 将分别切换你的分支。
4. 如果没有错误，请跳到下一项。你可能会看到类似内容：
   ```
   error: Your local changes to the following files would be overwritten by checkout:
        config.conf
        public/css/bg_load.css
        public/settings.json
   ```
   你会看到受影响的文件列表。如果你不关心这些设置文件被替换，则 `git switch -f release` 或 `git switch -f staging` 将设置你的分支。
   如果你希望保存这些更改，请从备份中恢复。

5. 输入 `npm install`，然后输入 `npm run start` 以测试一切是否正常运行。
6. 尽情享受！如果需要，从备份中恢复数据。

### fatal: invalid reference: release

如果你从旧的远程仓库（在迁移到组织仓库之前）仅克隆了一个分支，则可能会发生这种情况。要修复此问题，你需要从新的远程仓库添加并获取一个分支：

```
git remote add st https://github.com/SillyTavern/SillyTavern
git fetch st
git checkout -t st/release
```

然后从步骤 5 继续。

### ZIP 安装

对你来说没有变化。像往常一样下载分支/发布版本的 ZIP 文件即可。