
# 远程连接

通常，这是为那些希望在同一 WiFi 网络内的 PC 上运行 ST 服务器，同时在手机上使用 SillyTavern 的用户准备的。

这也是允许从本地网络外部进行远程连接的第一步。

> **⚠️ Warning**
>
> 你不应使用端口转发将 ST 服务器暴露到互联网上。请改用 VPN 或隧道服务，如 Cloudflare Zero Trust、ngrok 或 Tailscale。更多信息请参阅 [VPN 和隧道](/administration/tunneling/) 指南。


> **🚫 免责声明**
>
> **在未确保适当安全措施之前，切勿将任何实例托管在开放的互联网上。**
>
> **对于因安全措施不当或不足而导致未经授权访问所造成的任何损害或损失，我们概不负责。**


## 允许远程连接

默认情况下，ST 服务器仅接受来自其运行所在机器（localhost）的连接。要允许它监听来自其他设备的连接，请将 `config.yaml` 中的 `listen` 选项设置为 `true`。

> **📝 如果你直接在 SillyTavern 文件夹中搜索 `config.yaml`，可能会找到两个文件。**
>
> 本文档中对 `config.yaml` 的所有修改均指 SillyTavern 根目录下的那个（/SillyTavern/config.yaml），而非 `/SillyTavern/default/config.yaml`。


```yaml
# Listen for incoming connections
listen: true
```

当 ST 正在监听远程连接时，你应该会在控制台中看到以下消息：

```txt
SillyTavern is listening on IPv4: 0.0.0.0:8000
```

以及关于其含义的一些说明。

当 ST **未**监听远程连接时，你应该会在控制台中看到以下消息：

```txt
SillyTavern is listening on IPv4: 127.0.0.1:8000
```

## 访问控制配置

启用远程连接监听后，你必须至少配置一种访问控制方法。否则，服务器将无法启动。

### 基于白名单的访问控制

要通过白名单启用访问控制，请编辑 SillyTavern 根目录下的 `config.yaml` 文件（`/SillyTavern/config.yaml`）：

1. 至少启动一次 SillyTavern 以生成必要的配置文件。
2. 在文本编辑器中打开 `/SillyTavern/config.yaml`。
3. 找到 `whitelist` 部分并添加你希望允许的 IP 地址：
    * 每个 IP 地址单独列出。
    * 确保包含 `127.0.0.1`，否则你将无法从主机连接。
    * 支持单个 IP、CIDR 掩码（例如 `10.0.0.0/24`）和通配符（`*`）范围。
4. 保存 `config.yaml` 文件。
5. **重启你的 SillyTavern 服务器。**

#### `config.yaml` 白名单配置示例

1. 允许本地网络上的任何设备：

    ```yaml
    whitelist:
      - ::1
      - 127.0.0.1
      - 10.0.0.0/8
      - 172.16.0.0/12
      - 192.168.0.0/16
    ```

    如果不确定本地网络的地址范围，请使用上述白名单。

2. 允许两个特定设备连接：

    ```yaml
    whitelist:
      - ::1
      - 127.0.0.1
      - 192.168.0.2
      - 192.168.0.5
    ```

3. 允许 `192.168.0.*` 子网上的任何设备连接：

    ```yaml
    whitelist:
      - ::1
      - 127.0.0.1
      - 192.168.0.*
    ```

4. 允许所有 IPv4 设备的网络连接：

    ```yaml
    whitelist:
      - 0.0.0.0/0
    ```

### 禁用基于白名单的访问控制

要禁用基于白名单的访问控制：

* 在 `/SillyTavern/config.yaml` 中将 `whitelistMode` 设置为 `false`。
* 删除或重命名 SillyTavern 基础安装文件夹中的 `whitelist.txt`（如果存在）。
* 重启你的 SillyTavern 服务器。

### 不推荐：使用 `whitelist.txt`

> **ℹ️ Info**
>
> 如果 `whitelist.txt` 存在，它将优先于 `config.yaml` 中的白名单设置。
>
> 然而，由于所有其他配置都在 `config.yaml` 中管理，而 `whitelist.txt` 可能会遇到权限问题或被锁定，系统可能会静默回退到使用 `config.yaml` 白名单。
>
> **直接编辑 config.yaml 既更简单也更可靠。**


如果你仍然偏好使用 whitelist.txt：

1. 在 SillyTavern 基础安装文件夹中创建一个名为 `whitelist.txt` 的新文本文件。
2. 在文本编辑器中打开它并添加允许的 IP 地址。
3. 保存文件并重启你的 SillyTavern 服务器。

#### `whitelist.txt` 配置示例

```txt
10.0.0.0/8
172.16.0.0/12
192.168.0.0/16
127.0.0.1
::1
```

这允许本地网络上的任何设备连接。

### 通过 HTTP 基本身份验证进行访问控制

> **⚠️ Warning**
>
> HTTP 基本身份验证不提供强大的安全性。
>
> 没有速率限制来防止暴力破解攻击。如果这是一个顾虑，建议使用带 TLS 和速率限制的反向代理，以及专用的[身份验证服务](/administration/sso/)。


每当客户端通过 HTTP 连接时，服务器都会要求输入用户名和密码。**这仅在启用远程连接（listen: true）时有效。**

要启用 HTTP BA，请打开 SillyTavern 基础目录中的 `config.yaml` 并搜索 `basicAuthMode`。将 basicAuthMode 设置为 true 并设置用户名和密码。注意：`config.yaml` 仅在 ST 至少执行过一次后才会存在。

```yaml
basicAuthMode: true
basicAuthUser:
  username: "MyUsername"
  password: "MyPassword"
```

或者，你可以按如下方式启用基本身份验证：

```yaml
basicAuthMode: true
enableUserAccounts: true
perUserBasicAuth: true
```

在此 `perUserBasicAuth` 模式下，基本身份验证的用户名和密码将与任何设置了密码的有效多用户账户相同。此外，SillyTavern 将直接登录到该账户。**在启用 `perUserBasicAuth` 之前，请确保你有一个设置了密码的账户。**

保存文件并重启 SillyTavern（如果它已在运行）。连接到 ST 时，系统应提示你输入用户名和密码。用户名和密码均以明文传输。如果你对此有顾虑，可以通过 HTTPS 提供 ST 服务。

### 私有地址白名单

虽然默认允许从服务器向私有 IP 范围（例如 `192.168.x.x`、`10.x.x.x`）中的地址发起出站 HTTP 请求，但你可以使用白名单配置来限制对特定私有地址的访问。当你有一个运行在本地网络上的私有 API 希望允许 ST 访问，但又想阻止 ST 访问本地网络上的其他设备时，建议使用此功能。

#### 什么被视为“私有地址”？

* 回环地址：IPv4 为 `127.0.0.0/8`，IPv6 为 `::1/128`。
* IPv4 私有地址范围：A 类（`10.0.0.0/8`）、B 类（`172.16.0.0/12`）、C 类（`192.168.0.0/16`）。
* 链路本地地址：IPv4 为 `169.254.0.0/16`，IPv6 为 `fe80::/10`。
* 唯一本地地址：IPv6 为 `fc00::/7`。

#### 切换私有地址白名单

要启用私有地址白名单，请编辑 SillyTavern 根目录下的 `config.yaml` 文件：

```yaml
privateAddressWhitelist:
    enabled: true
```

#### 将私有地址添加到白名单

默认情况下，这仅允许从服务器向回环地址（`127.0.0.1` 和 `::1`）发起请求。要将更多私有地址添加到白名单，请将它们包含在 `privateAddressWhitelist.allowedRanges` 部分中：

```yaml
privateAddressWhitelist:
  allowedRanges:
    - "127.0.0.0/8"
    - "::1/128"
    - "192.168.0.0/16"
```

此示例允许从服务器向 `192.168.x.x` 范围内的任何地址和回环地址发起请求，同时仍然阻止对其他私有 IP 范围的访问。

### 主机白名单

在没有 HTTPS 的情况下通过网络托管服务器时，强烈建议启用请求主机验证。这有助于防止各种攻击，例如 DNS 重绑定。默认情况下，SillyTavern 服务器会在来自未识别主机的首次连接时记录一条控制台消息。

#### 切换主机白名单

要启用主机白名单，请编辑 SillyTavern 根目录下的 `config.yaml` 文件：

```yaml
hostWhitelist:
    enabled: true
```

#### 添加受信任的主机

要将主机名添加到受信任主机列表中，请将其包含在 `hostWhitelist.hosts` 部分中：

> **💡 提示**
>
> 不要添加 `localhost` 或 IP（如 `127.0.0.1` 或 `::1`）。这些始终被视为受信任的。
>
> 要添加一系列主机，请使用前导点。例如，添加 `.trycloudflare.com` 将信任 `trycloudflare.com` 以及任何子域名，如 `example.trycloudflare.com`。


```yaml
hostWhitelist:
  hosts:
    - "example.com"
    - ".trycloudflare.com"
```

#### 切换控制台消息

要禁用未识别主机的控制台消息，请将 `hostWhitelist.scan` 选项设置为 `false`：

```yaml
hostWhitelist:
    scan: false
```

## 连接到你的 SillyTavern 实例

### 获取 ST 主机机器的 IP 地址

设置好白名单后，你需要 ST 托管设备的 IP。

如果 ST 托管设备在同一 WiFi 网络上，你将使用 ST 主机的内部 WiFi IP：

* Windows：Windows 按钮 > 在搜索栏中输入 `cmd.exe` > 在控制台中输入 `ipconfig`，按回车 > 查找 `IPv4` 列表。

如果你（或其他人）想在不同网络下连接到你的 ST 托管实例，你需要 ST 托管设备的公网 IP。

* 在使用 ST 托管设备时，访问[此页面](https://whatismyipaddress.com/)并查找 `IPv4`。这就是你从远程设备连接时要使用的地址。

### 连接到 ST 服务器

无论你的情况最终得到什么 IP，你都需要将该 IP 地址和端口号输入到远程设备的网页浏览器中。

同一 WiFi 网络上 ST 主机的典型地址如下所示：

`http://192.168.0.5:8000`

使用 http:// 而非 https://

### 连接日志

到服务器的新连接会显示在控制台窗口中，并记录在 SillyTavern 数据目录的 `access.log` 文件中。

与服务器在同一台机器上的浏览器的控制台消息如下所示：

```txt
New connection from 127.0.0.1; User Agent: ...
```

与服务器在同一网络上但不同机器上的浏览器的控制台消息可能如下所示：

```txt
New connection from 192.168.116.187; User Agent: ...
```

如果连接被拒绝，控制台消息将如下所示：

```txt
New connection from 192.168.116.211; User Agent: ...

Forbidden: Connection attempt from 192.168.116.211. If you are attempting to connect, 
please add your IP address in whitelist or disable whitelist mode in config.yaml in 
root of SillyTavern folder.
```

`access.log` 将包含连接信息及时间戳，但不包含连接是被接受还是被拒绝。

### 故障排除

仍然无法连接？

* 如果连接尝试[出现在控制台中](#connection-logging)但被禁止，这是[白名单问题](#whitelist-based-access-control)。
* 如果 ST 正在监听远程连接但连接尝试未出现在控制台中，这是[网络问题](#network-issues)。
* 如果 ST 未监听远程连接，这是[读取问题](#allowing-remote-connections)。

#### 网络问题

* 在 Windows 上，应用程序可能被应用程序防火墙阻止。最快的解决方法是卸载并重新安装 node.js，当防火墙提示时，允许它访问网络。否则，你需要手动允许 node.js 应用程序通过 Windows 应用程序防火墙。
* 在 Windows 11 上，在设置 > 网络和 Internet > 以太网中启用专用网络配置文件类型。这对 Windows 11 非常重要，否则即使有上述防火墙规则，你也无法连接。
* 在 Linux 上，你可能需要通过防火墙允许该端口。执行此操作的命令是 `sudo ufw allow 8000`。这将允许端口 8000 上的流量。

不要修改路由器上的端口转发设置。这对于在本地网络内访问 ST 是不必要的，并且可能将你的服务器暴露到互联网上。

如果你正在尝试从[本地网络外部](/usage/remoteconnections/)访问你的 ST 服务器，但无法正常工作，请确定问题是出在远程设备与隧道/VPN 端点之间，还是出在服务器上的隧道端点与 ST 服务之间。否则你将花费大量时间排查错误的问题。

## HTTPS

### 使用 TLS/SSL 启动 SillyTavern

> **💡 Tip**
>
> SSL 也可以通过 `config.yaml` 文件进行配置：[SSL 配置](/administration/config-yaml/#ssl-configuration)。


要加密与你的 ST 实例之间的流量，请使用 `--ssl` 标志启动服务器。

示例：

```bash
node server.js --ssl
```

默认情况下，ST 会在 `certs` 文件夹中查找你的证书。如果你的文件位于其他地方，可以使用 `--keyPath` 和 `--certPath` 参数。

示例：

```bash
node server.js --ssl --keyPath /home/user/certificates/privkey.pem --certPath /home/user/certificates/cert.pem
```

运行 SillyTavern 的用户需要对证书文件具有读取权限。

### 如何获取证书

获取证书最简单、最快捷的方法是使用 [certbot](https://letsencrypt.org/getting-started/)。

### Docker 中的证书

> **⚠️ Warning**
>
> 出于安全和隐私原因，如果你正在构建 Docker 镜像，请不要将 SSL 证书包含在 Docker 镜像中。而应使用卷挂载在运行时提供证书。


在 Docker 中运行 SillyTavern 时，提供 SSL 证书的推荐方法是将其放置在 `/config` 卷挂载中。这样你无需重建容器镜像即可管理证书。

1. 将你的证书文件（例如 `privkey.pem` 和 `cert.pem`）放置在本地配置目录中，该目录挂载到容器中的 `/config`。

2. 更新你的 `config.yaml` 以引用证书：

    ```yaml
    ssl:
      enabled: true
      certPath: ./config/cert.pem
      keyPath: ./config/privkey.pem
    ```

3. 重启你的 Docker 容器以应用更改。