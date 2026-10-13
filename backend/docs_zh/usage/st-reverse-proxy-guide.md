
> **🚫 注意**
>
> 本节**不**涉及 OpenAI/Claude 反向代理。它仅指 **HTTP/HTTPS 反向代理**。


Termux 设置起来让你感到困惑吗？你是否厌倦了在每个设备上更新和安装 ST？想要组织你的聊天记录和角色？那么你很幸运。本指南将_希望_介绍如何在你自己的 PC 上托管 SillyTavern，让你可以从任何地方连接，并与你在同一台用于运行 AI 模型的 PC 上的机器人聊天！

> **⚠️ 警告**
>
> 本指南**不适合**初学者。技术性非常强。


## 友好提示

> **ℹ️ 对于 Windows 用户**
>
> 本指南不适用于 Windows 用户。我们建议使用 Linux 虚拟机或 WSL2 来遵循本指南。


> **ℹ️ 对于 Linux 用户**
>
> 你必须具备以下方面的先备知识：
>
> - Linux 控制台命令
> - DNS 记录
> - 公网 IP 地址
> - [Docker](https://www.docker.com)

> **📝 提示**

**你需要为自己购买一个域名，并为你的 SillyTavern 页面配置一个 `CNAME`。我们建议在 [Cloudflare](https://www.cloudflare.com) 上添加或购买域名，因为本指南将介绍如何通过 Cloudflare 本身来实现。**

## 安装

### Linux（裸机 SillyTavern）

对于 Linux，我们将通过 [Traefik](https://traefik.io/traefik/) 对 SillyTavern 进行反向代理。还有其他选项，例如 _NGINX_ 或 _Caddy_，但在本指南中，我们将使用 Traefik，因为这是我们自己使用的工具。

1. 使用 `ifconfig` 或从路由器获取计算机的私有 IP。
> **ℹ️ 提示**
>
>    建议将你的私有 IP 设置为静态 IP。请参阅路由器的用户手册或通过 Google 搜索如何配置静态 IP。

2. 通过谷歌搜索 `what's my ip` 获取你的调制解调器的公网 IP。
> **ℹ️ 关于公网 IP**
>
>    大多数住宅/家庭网络使用**动态 IP**，这些 IP 在使用数月后会被更新。如果你拥有动态 IP，请使用 DDClient，或者记住定期检查并在 Cloudflare 仪表板上更改你的公网 IP。

3. 按照此处 [Docker 安装指南](https://docs.docker.com/engine/install/) 的步骤安装 Docker。
> **🚫 注意**
>
>    **不要**安装 Docker Desktop。

4. 按照此处 [Docker 安装后指南](https://docs.docker.com/engine/install/linux-postinstall/) 中**将 Docker 作为非 root 用户管理**的步骤操作。
5. 进入 Linux 的根目录，创建一个名为 `docker` 的新文件夹。
    ```sh
    cd /
    sudo mkdir docker && cd docker
    ```
6. 执行 `chown`，将 _<USER>_ 替换为你的 Linux 用户名，以设置 docker 文件夹的权限。
    ```sh
    sudo chown -R <USER>:<USER> .
    ```
7. 在 _docker_ 文件夹内创建一个名为 `secrets` 的文件夹，并在 _secrets_ 内创建一个名为 `cloudflare` 的文件夹。
    ```sh
    mkdir secrets && mkdir secrets/cloudflare
    ```
8. 在 _docker_ 文件夹内创建一个名为 `appdata` 的文件夹，并在 _appdata_ 内创建一个名为 `traefik` 的文件夹。然后进入 `appdata/traefik` 文件夹。
    ```sh
    mkdir appdata && mkdir appdata/traefik
    cd appdata/traefik
    ```
9. 使用 `touch` 创建一个 _acme.json_ 文件，并将其权限设置为 600。
    ```sh
    touch acme.json
    chmod 600 acme.json
    ```
10. 使用 `nano` 或类似的编辑器，创建一个名为 _traefik.yml_ 的文件并粘贴以下内容。将模板邮箱替换为你自己的邮箱，然后保存文件。
    ```yml
    api:
        dashboard: true
        debug: true
        insecure: true
    entryPoints:
        http:
            address: ":80"
            http:
                redirections:
                    entryPoint:
                        to: https
                        scheme: https
        https:
            address: ":443"
    serversTransport:
        insecureSkipVerify: true
    providers:
        docker:
            endpoint: "unix:///var/run/docker.sock"
            exposedByDefault: false
        file:
            filename: /config.yml
            watch: true
    certificatesResolvers:
        cloudflare:
            acme:
                email: YOUR_CLOUDFLARE_EMAIL@DOMAIN.com
                storage: acme.json
                dnsChallenge:
                    provider: cloudflare
                    #disablePropagationCheck: true  # 如果你在通过 cloudflare 拉取证书时遇到问题，请取消注释此行。将此标志设置为 true 将禁用等待 TXT 记录传播到所有权威名称服务器的需求。
                    resolvers:
                        - "1.1.1.1:53"
                        - "1.0.0.1:53"
    ```
11. 返回到 `docker` 文件夹。
    ```sh
    cd /docker
    ```
12. 使用 `nano` 或类似的编辑器，创建一个名为 _docker-compose.yaml_ 的文件并粘贴以下内容。然后保存文件。

    ```yaml
    secrets:
        CF_DNS_API_KEY:
            file: ./secrets/cloudflare/CF_DNS_API_KEY

    services:
        traefik:
            image: traefik:latest
            container_name: traefik
            restart: unless-stopped
            secrets:
                - CF_DNS_API_KEY
            ports:
                - 80:80
                - 443:443
                - 8080:8080
            environment:
                CLOUDFLARE_DNS_API_TOKEN_FILE: /run/secrets/CF_DNS_API_KEY
                CLOUDFLARE_ZONE_API_TOKEN_FILE: /run/secrets/CF_DNS_API_KEY
            volumes:
                - /var/run/docker.sock:/var/run/docker.sock:ro
                - ./appdata/traefik/traefik.yml:/traefik.yml:ro
                - ./appdata/traefik/config.yml:/config.yml:ro
                - ./appdata/traefik/acme.json:/acme.json
                - /etc/localtime:/etc/localtime:ro

    networks:
        internal:
            driver: bridge
    ```

13. 登录 Cloudflare，点击你的域名，然后点击 **Get your API token**。
14. 点击 _Create Token_，然后点击 _Create Custom Token_，并确保你的令牌具有以下权限。
> **ℹ️ 令牌权限**
>
> **Zone -> DNS -> Edit**
>
> **Zone -> Zone -> Read**


    点击 _Continue to summary_，然后点击 _Create Token_。

15. 复制给你的令牌密钥，并将其安全地存储起来。
16. `cd` 进入 `secrets/cloudflare`，使用 `nano` 或类似的编辑器，创建一个名为 **CF_DNS_API_KEY** 的文件，并将你的密钥粘贴进去。
17. 返回到你的域名页面，进入 **DNS**。使用 **Add record** 创建一条新记录，并像下面这样创建两个 _A_ 类型的键。将 `PUBLIC_IP` 替换为你自己的公网 IP，然后点击 _Save_。

    | 类型 | 名称（必需） | 目标（必需） | 代理状态 | TTL  |
    |------|-----------------|-------------------|--------------|------|
    | A    | DOMAIN.com      | PUBLIC_IP         | 已代理      | 自动 |
    | A    | www             | PUBLIC_IP         | 已代理      | 自动 |

18. 再创建一条 **`CNAME`** 类型的记录，然后点击 _Save_。下面是它在 Cloudflare 仪表板上的显示示例。

    | 类型  | 名称（必需） | 目标（必需） | 代理状态 | TTL |
    |-------|-----------------|-------------------|--------------|-----|
    | CNAME | silly           | DOMAIN.com        | 已代理      | 不适用 |

19. `cd` 进入 _appdata/traefik_，使用 `nano` 或类似的编辑器，创建一个名为 _config.yml_ 的文件并粘贴以下内容。将 `PRIVATE_IP` 替换为你获取的私有 IP，将 `silly.DOMAIN.com` 替换为你的子域名和域名页面名称，然后保存文件。

    ```yml
    http:
        routers:
            sillytavern:
                entryPoints:
                    - "https"
                rule: "Host(`silly.DOMAIN.com`)"
                middlewares:
                    - https-redirectscheme
                tls: {}
                service: sillytavern

        services:
            sillytavern:
                loadBalancer:
                    servers:
                        - url: "http://PRIVATE_IP:8000"
                    passHostHeader: true

        middlewares:
            https-redirectscheme:
                redirectScheme:
                    scheme: https
                    permanent: true
    ```

20. 使用以下命令运行 Docker Compose：
    ```sh
    cd /docker
    docker compose up -d
    ```
21. 进入你的 SillyTavern 文件夹，编辑 `config.yaml` 以启用监听模式和基本认证，同时禁用 `whitelistMode`。

    ```yaml
    listen: yes
    whitelistMode: false
    basicAuthMode: true
    ```

> **⚠️ 提示**
>
>    确保将默认用户名和密码更改为你可以记住的强密码。


    或者使用 SillyTavern 账户作为用户名和密码：

    ```yaml
    basicAuthMode: true
    enableUserAccounts: true
    perUserBasicAuth: true
    ```

> **⚠️ 提示**
>
> 在启用 perUserBasicAuth 之前，请确保你拥有有效的多用户设置以及可用的密码。


22. 等待几分钟，然后打开你为 ST 创建的域名页面。最后，你应该能够仅凭一个 URL 和一个账户从任何地方打开 SillyTavern。
> **ℹ️ 提示**
>
> 如果几分钟后没有任何反应，请检查 Traefik 的容器日志以查找可能的错误。

23. 尽情享受吧！:D

### Linux（Docker SillyTavern）

> **⚠️ 注意**
>
> 请注意，我们在裸机上运行 SillyTavern，而不是通过 Docker。以下是我们对 Docker 上与其他我们通常与 ST 一起使用的 Docker 容器一起运行时的一个大致思路。


1. 遵循 **Linux（裸机 SillyTavern）** 的第 1-11 步。
2. 登录 Cloudflare，点击你的域名，然后点击 **Get your API token**。
3. 点击 _Create Token_，然后点击 _Create Custom Token_，并确保你的令牌具有以下权限。
> **ℹ️ 令牌权限**
>
>    **Zone -> DNS -> Edit**
>
>     **Zone -> Zone -> Read**


    点击 _Continue to summary_，然后点击 _Create Token_。

4. 复制给你的令牌密钥，并将其安全地存储起来。
5. `cd` 进入 `secrets/cloudflare`，使用 `nano` 或类似的编辑器，创建一个名为 **CF_DNS_API_KEY** 的文件，并将你的密钥粘贴进去。
6. 返回到你的域名页面，进入 **DNS**。使用 **Add record** 创建一条新记录，并像下面这样创建两个 _A_ 类型的键。将 `PUBLIC_IP` 替换为你自己的公网 IP，并将示例域名替换为你的域名，然后点击 _Save_。

    | 类型 | 名称（必需） | 目标（必需） | 代理状态 | TTL  |
    |------|-----------------|-------------------|--------------|------|
    | A    | DOMAIN.com      | PUBLIC_IP         | 已代理      | 自动 |
    | A    | www             | PUBLIC_IP         | 已代理      | 自动 |

7. 再创建一条 **`CNAME`** 类型的记录，然后点击 _Save_。下面是它在 Cloudflare 仪表板上的显示示例。

    | 类型  | 名称（必需） | 目标（必需） | 代理状态 | TTL |
    |-------|-----------------|-------------------|--------------|-----|
    | CNAME | silly           | DOMAIN.com        | 已代理      | 不适用 |

8. 将 SillyTavern 的 Git 仓库克隆到 `docker` 文件夹中。
    ```sh
    cd /docker && git clone https://github.com/SillyTavern/SillyTavern
    ```
9. 使用 `nano` 或类似的编辑器，创建一个名为 _docker-compose.yaml_ 的文件并粘贴以下内容。将 `silly.DOMAIN.com` 替换为你上面添加的子域名，然后保存文件。

    ```yaml
    secrets:
        CF_DNS_API_KEY:
            file: ./secrets/cloudflare/CF_DNS_API_KEY

    services:
        traefik:
            image: traefik:latest
            container_name: traefik
            restart: unless-stopped
            secrets:
                - CF_DNS_API_KEY
            ports:
                - "80:80"
                - 443:443
                - 8080:8080
            environment:
                CLOUDFLARE_DNS_API_TOKEN_FILE: /run/secrets/CF_DNS_API_KEY
                CLOUDFLARE_ZONE_API_TOKEN_FILE: /run/secrets/CF_DNS_API_KEY
            volumes:
                - /var/run/docker.sock:/var/run/docker.sock:ro
                - ./appdata/traefik/traefik.yml:/traefik.yml:ro
                - ./appdata/traefik/config.yml:/config.yml:ro
                - ./appdata/traefik/acme.json:/acme.json
                - /etc/localtime:/etc/localtime:ro
        sillytavern:
            build: ./SillyTavern
            container_name: sillytavern
            hostname: sillytavern
            image: ghcr.io/sillytavern/sillytavern:latest
            volumes:
                - "./appdata/sillytavern/config:/home/node/app/config"
                - "./appdata/sillytavern/data:/home/node/app/data"
            restart: unless-stopped
            labels:
                - "traefik.enable=true"
                - "traefik.http.routers.sillytavern.entrypoints=http"
                - "traefik.http.routers.sillytavern.rule=Host(`silly.DOMAIN.com`)"
                - "traefik.http.middlewares.sillytavern-https-redirect.redirectscheme.scheme=https"
                - "traefik.http.routers.sillytavern.middlewares=sillytavern-https-redirect"
                - "traefik.http.routers.sillytavern-secure.entrypoints=https"
                - "traefik.http.routers.sillytavern-secure.rule=Host(`silly.DOMAIN.com`)"
                - "traefik.http.routers.sillytavern-secure.tls=true"
                - "traefik.http.routers.sillytavern-secure.service=sillytavern"
                - "traefik.http.services.sillytavern.loadbalancer.server.port=8000"

    networks:
        internal:
            driver: bridge
    ```

10. 使用以下命令运行 Docker Compose：
    ```sh
    docker compose up -d
    ```
11. 停止 SillyTavern Docker 容器。
    ```sh
    docker compose stop sillytavern
    ```
12. 进入你的 SillyTavern 文件夹（`appdata/sillytavern/config`），编辑 `config.yaml` 以启用监听模式和基本认证，同时禁用 `whitelistMode`。

    ```yaml
    listen: yes
    whitelistMode: false
    basicAuthMode: true
    ```

> **⚠️ 提示**
>
>    确保将默认用户名和密码更改为你可以记住的强密码。


13. 再次启动 SillyTavern Docker 容器。
    ```sh
    docker compose up -d sillytavern
    ```
14. 等待几分钟，然后打开你为 ST 创建的域名页面。最后，你应该能够仅凭一个 URL 和一个账户从任何地方打开 SillyTavern。
> **ℹ️ 提示**
>
> 如果几分钟后没有任何反应，请检查 Traefik 的容器日志以查找可能的错误。

15. 尽情享受吧！:D

## 更新你的 Cloudflare DNS

[**DDClient**](https://ddclient.net/) 允许你在 ISP 更改你的公网 IP 时将你的公网 IP 同步到 Cloudflare，从而让你能够继续访问你的 ST 实例，就像什么都没发生过一样。