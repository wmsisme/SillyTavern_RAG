
# Docker 安装

> **📝 提示**
以下说明假定您已安装 Docker，能够访问命令行以安装容器，并熟悉其常规操作。
> **📝 提示**

## 使用 GitHub 容器注册表

使用预构建镜像是开始使用 SillyTavern 在 Docker 中最快捷、最简单的方法。您可以从 GitHub 容器注册表拉取最新镜像。

### Docker Compose（推荐）

从 [GitHub 仓库](https://github.com/SillyTavern/SillyTavern/blob/release/docker/docker-compose.yml) 下载 `docker-compose.yml` 文件，并在文件所在目录中运行以下命令。这将从 GitHub 容器注册表拉取最新的发布镜像并启动容器，自动创建必要的卷。

```sh
docker compose up
```

您可以编辑文件并根据需要应用自定义配置：

- 默认端口为 8000。您可以通过修改 `ports` 部分来更改它。
- 如果您想使用开发分支而非稳定版，请将 `image` 标签更改为 `staging`。
- 如果您想使用环境变量调整服务器配置，请查看[环境变量](/administration/config-yaml/#environment-variables)页面。

### Docker CLI（高级）

您需要两个必需的目录映射和一个端口映射，以使 SillyTavern 正常运行。在命令中，替换以下位置的选择项：

#### 容器变量

##### 卷映射

- `CONFIG_PATH` - SillyTavern 配置文件将存储在宿主机上的目录
- `DATA_PATH` - SillyTavern 用户数据（包括角色）将存储在宿主机上的目录
- `PLUGINS_PATH` - （可选）SillyTavern 服务器插件将存储在宿主机上的目录
- `EXTENSIONS_PATH` - （可选）全局 UI 扩展将存储在宿主机上的目录

##### 端口映射

- `PUBLIC_PORT` - 暴露流量的端口。这是必需的，因为您将从其虚拟机容器外部访问实例。在没有单独的安全服务的情况下，**不要**将此端口暴露到互联网。

##### 额外设置

- `SILLYTAVERN_VERSION` - 在 [GitHub 软件包页面](https://github.com/SillyTavern/SillyTavern/pkgs/container/sillytavern) 上，您会看到已标记镜像版本的列表。镜像标签 "latest" 将使您保持当前发布版本的更新。您也可以使用指向相应分支每晚构建镜像的 "staging"。

#### 运行容器

1. 打开命令行
2. 在您希望存储配置和数据文件的文件夹中运行以下命令：

```bash
SILLYTAVERN_VERSION="latest"
PUBLIC_PORT="8000"
CONFIG_PATH="./config"
DATA_PATH="./data"
PLUGINS_PATH="./plugins"
EXTENSIONS_PATH="./extensions"

docker run \
  --name="sillytavern" \
  -p "$PUBLIC_PORT:8000/tcp" \
  -v "$CONFIG_PATH:/home/node/app/config:rw" \
  -v "$DATA_PATH:/home/node/app/data:rw" \
  -v "$EXTENSIONS_PATH:/home/node/app/public/scripts/extensions/third-party:rw" \
  -v "$PLUGINS_PATH:/home/node/app/plugins:rw" \
  ghcr.io/sillytavern/sillytavern:"$SILLYTAVERN_VERSION"
```

> **💡 Tip**
>
> 默认情况下，容器将在前台运行。如果您希望在后台运行，请将 `-d` 标志添加到 `docker run` 命令中。


## 构建 Docker 镜像

> **ℹ️ Info**
>
> 以下部分假设您已将 SillyTavern 安装到非根（非管理员）文件夹中。如果您将 SillyTavern 安装到了根文件夹，则可能需要使用管理员权限（`sudo`、`doas`、命令提示符（管理员））运行其中一些命令。


如果您想自行构建 Docker 镜像，可以按照以下步骤操作。这对于自定义镜像或用于开发用途非常有用。

### Linux

1. 按照 [此处](https://docs.docker.com/engine/install/) 的 Docker 安装指南安装 Docker。
> **🚫 Danger**
>
>    **不要**安装 Docker Desktop。

2. 按照 Docker [安装后指南](https://docs.docker.com/engine/install/linux-postinstall/) 中的 **将 Docker 作为非根用户管理** 步骤操作。
3. 使用您的包管理器安装 [Git](https://git-scm.com/download/linux)。

    - Debian (Ubuntu/Pop! OS 等)

        ```sh
        sudo apt install git
        ```

    - Arch Linux (Manjaro/EndeavourOS 等)

        ```sh
        sudo pacman -S git
        ```

    - Fedora、Red Hat Enterprise Linux (RHEL) 等
        ```sh
        sudo dnf install git
        ```

4. 克隆 SillyTavern 仓库。

    - 发布版（稳定分支）

        ```sh
        git clone https://github.com/SillyTavern/SillyTavern && cd SillyTavern/docker
        ```

    - 暂存版（开发分支）
        ```sh
        git clone https://github.com/SillyTavern/SillyTavern -b staging && cd SillyTavern/docker
        ```

5. 在 Docker 文件夹内运行以下命令来执行 `docker compose`。

    ```sh
    docker compose up -d
    ```

6. 打开新浏览器并访问 [http://localhost:8000](http://localhost:8000)。稍后您应该会看到 SillyTavern 加载完成。

### Windows

> **⚠️ 关于 Windows 上的 Docker**
>
> 在 Windows 上使用 Docker **_真的_**很复杂。您不仅需要在 _打开或关闭 Windows 功能_ 中激活 _适用于 Linux 的 Windows 子系统_，还需要根据 PC 制造商（或主板制造商）的不同配置虚拟化（Intel VT-d/AMD SVM）。有时，某些系统上不存在此选项。
>
> 强烈建议您按照我们的 [Windows](/installation/windows/) 指南安装 SillyTavern。本节仅提供在 Windows 上实现此操作的一个 _大致_ 思路。


1.  按照 [此处](https://docs.docker.com/desktop/setup/install/windows-install/) 的 Docker 安装指南安装 Docker Desktop。
2.  安装 [Git for Windows](https://git-scm.com/download/win)。
3.  克隆 SillyTavern 仓库。

    -   发布版（稳定分支）

        ```sh
        git clone https://github.com/SillyTavern/SillyTavern && cd SillyTavern/docker
        ```

    -   暂存版（开发分支）
        ```sh
        git clone https://github.com/SillyTavern/SillyTavern -b staging && cd SillyTavern/docker
        ```

4.  在 Docker 文件夹内运行以下命令来执行 `docker compose`。

    ```sh
    docker compose up -d
    ```

5.  打开新浏览器并访问 [http://localhost:8000](http://localhost:8000)。稍后您应该会看到 SillyTavern 加载完成。

### macOS

> **📝 提示**
尽管 macOS 与 Linux 类似，但它没有 Docker 引擎。您需要像 Windows 一样安装 Docker Desktop。
您还需要安装 [Homebrew](https://brew.sh/) 以便在 Mac 上安装 Git。本节仅提供在 macOS 上实现此操作的一个 _大致_ 思路。
> **📝 提示**

1.  按照 [此处](https://docs.docker.com/desktop/setup/install/mac-install/) 的 Docker 安装指南安装 Docker Desktop。
2.  使用 Homebrew 安装 `git`。

    ```sh
    brew install git
    ```

3.  克隆 SillyTavern 仓库。

    -   发布版（稳定分支）

        ```sh
        git clone https://github.com/SillyTavern/SillyTavern && cd SillyTavern/docker
        ```

    -   暂存版（开发分支）
        ```sh
        git clone https://github.com/SillyTavern/SillyTavern -b staging && cd SillyTavern/docker
        ```

4.  在 Docker 文件夹内运行以下命令来执行 `docker compose`。

    ```sh
    docker compose up -d
    ```

5.  打开新浏览器并访问 [http://localhost:8000](http://localhost:8000)。稍后您应该会看到 SillyTavern 加载完成。

## 配置 SillyTavern

SillyTavern 的配置文件（config.yaml）将位于 `config` 文件夹中。配置该文件与在无 Docker 环境下配置没有区别，但您需要运行 `nano` 或具有管理员权限的代码编辑器才能保存更改。

> **⚠️ Warning**
>
> 不要忘记重启 SillyTavern 的 Docker 容器以应用更改！请确保在 `docker` 文件夹内执行此命令。

```sh
docker compose restart sillytavern
```

> **📝 提示**

## 定位用户数据

SillyTavern 的数据文件夹将位于 `data` 文件夹内。备份文件应该很容易，但恢复或添加内容可能需要使用管理员权限。

## 运行服务器插件

在 Docker 中运行插件（如 [HoYoWiki-Scraper-TS](https://github.com/Bronya-Rand/HoYoWiki-Scraper-TS) 或 [SillyTavern-Fandom-Scraper](https://github.com/SillyTavern/SillyTavern-Fandom-Scraper)）与在没有 Docker 的系统上运行没有区别，但我们需要对 Docker Compose 脚本进行一些修改才能实现。

> **📝 注意**
>
> 如果您已经在 `docker` 文件夹中看到 _plugins_ 文件夹，则可以跳过步骤 1-2。


1. 使用 `nano` 或代码编辑器打开 _docker-compose.yml_，并在 `volumes` 下方添加以下行：

    ```sh
        volumes:
            - "./config:/home/node/app/config"
            - "./data:/home/node/app/data"
            - "./plugins:/home/node/app/plugins"
    ```

2. 在 `docker` 文件夹中创建一个名为 _plugins_ 的新文件夹。
3. 按照插件的说明安装插件。
4. 使用 `nano` 或具有管理员权限的代码编辑器打开 _config.yaml_（位于 `config` 文件夹内），并启用 `enableServerPlugins`：

    ```sh
    enableServerPlugins: true
    ```

5. 重启 Docker 容器。

    ```sh
    docker compose restart sillytavern
    ```

## 非根用户模式

默认情况下，容器以 root 身份运行。如果您希望挂载卷中创建的文件由特定的宿主用户拥有（例如，避免 root 拥有的文件），可以启用非根模式。

### 选项 1：PUID/PGID（推荐）

设置 `PUID` 和 `PGID` 环境变量为您希望容器使用的 UID/GID。入口点将更新所需目录的所有权，然后以映射的用户身份运行服务器。

Docker Compose 示例：

```yaml
services:
  sillytavern:
    environment:
      - PUID=1000
      - PGID=1000
```

Docker CLI 示例：

```bash
docker run \
  --name="sillytavern" \
  -e PUID=1000 \
  -e PGID=1000 \
  -p "$PUBLIC_PORT:8000/tcp" \
  -v "$CONFIG_PATH:/home/node/app/config:rw" \
  -v "$DATA_PATH:/home/node/app/data:rw" \
  -v "$EXTENSIONS_PATH:/home/node/app/public/scripts/extensions/third-party:rw" \
  -v "$PLUGINS_PATH:/home/node/app/plugins:rw" \
  ghcr.io/sillytavern/sillytavern:"$SILLYTAVERN_VERSION"
```

### 选项 2：Docker `--user` 标志

您也可以使用 Docker 的 `--user` 标志以特定用户身份运行容器。在此模式下，容器无法自动修复权限，因此请确保您提供的 UID/GID 对已挂载的卷具有写权限。

```bash
docker run \
  --name="sillytavern" \
  --user 1000:1000 \
  -p "$PUBLIC_PORT:8000/tcp" \
  -v "$CONFIG_PATH:/home/node/app/config:rw" \
  -v "$DATA_PATH:/home/node/app/data:rw" \
  -v "$EXTENSIONS_PATH:/home/node/app/public/scripts/extensions/third-party:rw" \
  -v "$PLUGINS_PATH:/home/node/app/plugins:rw" \
  ghcr.io/sillytavern/sillytavern:"$SILLYTAVERN_VERSION"
```

## 容器健康检查

Docker 镜像包含一个内置的健康检查机制，用于监控 SillyTavern 服务器的响应能力。这对于容器编排系统（如 Docker Compose、Kubernetes 或 Docker Swarm）检测并自动重启无响应的容器非常有用。

### 工作原理

健康检查使用心跳文件机制：

1. 启用后，SillyTavern 服务器会定期向数据目录中的 `heartbeat.json` 文件写入时间戳。
2. 健康检查脚本（`src/healthcheck.js`）验证心跳文件是否存在以及是否最近更新。
3. 如果心跳文件缺失或过旧（超过 2 个缺失间隔），容器将被标记为不健康。

### 配置

> **⚠️ Warning**
>
> 健康检查脚本不支持通过命令行参数覆盖数据目录。如果您将数据目录从默认的 `/home/node/app/data` 更改，请确保相应地设置 `SILLYTAVERN_DATAROOT` 环境变量。


健康检查由 `SILLYTAVERN_HEARTBEATINTERVAL` 环境变量（或 config.yaml 中的 `heartbeatInterval`）控制。该值指定心跳写入之间的间隔（秒）。

- **默认值：** `0`（禁用）
- **推荐值：** 使用 Docker 健康检查时设为 `30` 秒

默认的 `docker-compose.yml` 文件包含启用心跳的健康检查配置：

```yaml
services:
  sillytavern:
    environment:
      - SILLYTAVERN_HEARTBEATINTERVAL=30
    healthcheck:
      test: ["CMD", "node", "src/healthcheck.js"]
      interval: 30s
      timeout: 10s
      start_period: 20s
      retries: 3
```

### 检查容器健康状态

您可以使用以下命令检查容器的健康状态：

```sh
docker inspect --format='{{.State.Health.Status}}' sillytavern
```

或者查看包括健康状态的完整容器状态：

```sh
docker ps
```

`STATUS` 列将显示 `healthy`、`unhealthy` 或 `starting`，以及运行时间。

### 禁用健康检查

如果您不需要健康检查功能，可以通过以下方式禁用它：

1. 将环境变量设置为 `0`：

    ```yaml
    environment:
      - SILLYTAVERN_HEARTBEATINTERVAL=0
    ```

2. 删除或注释掉 `docker-compose.yml` 中的 `healthcheck` 部分。

## Docker 常见问题

### 挂载卷的 SELinux 权限问题

启用了 SELinux 的 Linux 发行版（如 RHEL、CentOS、Fedora 等）可能会因安全策略阻止 Docker 容器访问挂载卷。这可能导致容器尝试读取或写入挂载目录时出现权限被拒绝的错误。

可以向卷挂载添加后缀 `:z` 或 `:Z`。这些后缀告诉 Docker 重新标记共享卷上的文件对象。

- 当卷内容将在容器之间共享时，使用 `z` 选项。
- 当卷内容仅供当前容器使用时，使用 `Z` 选项。

示例：

```yaml
# docker-compose.yml
volumes:
  ## 共享卷
  - ./config:/home/node/app/config:z
  ## 私有卷
  - ./data:/home/node/app/data:Z
```

### 被白名单禁止

> **⚠️ Docker Desktop 与 Docker CE**
>
> [whitelistDockerHosts](/administration/config-yaml/#ip-whitelisting) 配置选项（默认启用）通过解析 `host.docker.internal` 和 `gateway.docker.internal` 主机名来工作。这些主机名 **仅在 Docker Desktop（Windows/Mac）中可用**。如果您在 **Linux 上使用 Docker CE**，这些主机名将无法解析，自动白名单将失败，并在容器日志中出现类似以下的错误：

```
Failed to resolve whitelist hostname host.docker.internal: getaddrinfo ENOTFOUND host.docker.internal
Failed to resolve whitelist hostname gateway.docker.internal: getaddrinfo ENOTFOUND gateway.docker.internal
```

在这种情况下，您需要手动将 Docker 网关 IP 添加到白名单，如下所述。
> **📝 提示**

1. 执行以下 Docker 命令获取 SillyTavern Docker 容器的 IP。

    ```sh
    docker network inspect docker_default
    ```

    您应该会得到类似以下的输出。

    ```json
    [
        {
            "Name": "docker_default",
            "IPAM": {
                "Config": [
                    {
                        "Subnet": "172.18.0.0/16",
                        "Gateway": "172.18.0.1"
                    }
                ]
            }
        }
    ]
    ```

    记下 _Gateway_ 中的 IP，这很重要。

2. 使用管理员权限运行您选择的文本编辑器，进入 `config` 文件夹并打开 `config.yaml`。

    在编辑器中，向下滚动到 `whitelist` 部分。您应该会看到类似以下的内容。

    ```yaml
    whitelist:
        - 127.0.0.1
    ```

    在 _127.0.0.1_ 下方添加新行，并填入您从 Docker 复制的 IP。之后应该类似如下：

    ```yaml
    whitelist:
        - 127.0.0.1
        - 172.18.0.1
    ```

    保存文件并退出文本编辑器。

> **ℹ️ Info**
>
> 请注意，如果您将 Docker 网络配置为桥接模式，您也可以像往常一样将外部 IP 地址添加到白名单中。


3. 重启 Docker 容器以应用新配置。

    ```sh
    docker compose restart sillytavern
    ```