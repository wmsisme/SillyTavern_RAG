
VPN 和隧道是从世界任何地方安全访问家庭网络的一种方式。本指南将向你展示如何使用 VPN 或隧道从任何地方访问你的 SillyTavern 实例。

## 方法

1. 使用**自建 VPN**。

   一些路由器在路由器管理页面中自带托管 VPN 服务器（主要是 OpenVPN 或 WireGuard）的功能。请参阅你的路由器手册来设置 VPN，并将你的设备添加到 VPN 中。连接后，只需前往你为 SillyTavern 设置的私有 IP，即可正常连接。对用户和 Windows 使用来说更简单。

2. 使用 [**Cloudflare Zero Trust**](https://developers.cloudflare.com/cloudflare-one/)。

   Cloudflare Zero Trust 是 Cloudflare 中的一项免费组织功能，允许你添加 50 个用户。这将通过 Cloudflare 代理你的流量，并通过使用 `cloudflared` 将你的 ST 电脑添加为隧道，你可以像在家一样连接到你的 ST 实例。

   请注意，创建隧道后，你必须为路由器的私有 IP 地址添加路由，并计算 IP CIDR 值，以便在使用 Cloudflare Zero Trust 时在外出时获得完整的本地访问权限。

3. 使用独立的 **Cloudflare** 或 **[ngrok](https://ngrok.com)** 隧道。

   与 AI 后端可以连接的方式类似，你也可以通过 Cloudflare Tunnel 连接你的 ST 实例并打开 Cloudflare Tunnel 页面。但是，每次你想在外出时使用 ST 时，都必须复制并粘贴 Cloudflare/NGROK 生成的每个新链接。

4. 使用 **Tailscale**。

   Tailscale 是一个 VPN 提供商，可实现与你的 PC 的安全远程连接。

## Tailscale 设置

Tailscale 是一个 VPN 提供商，可实现与你的 PC 的安全远程连接。Tailscale 服务器存在一个开源实现，你也可以使用 [Headscale](https://github.com/juanfont/headscale) 托管服务器，但这超出了本教程的范围。

### 1. 创建账户

* 前往 [Tailscale 网站](https://tailscale.com/)并创建一个新账户。

**注意：** 对于单个人员的日常使用，Tailscale 将永久免费。如果你担心隐藏费用，只需不添加任何支付选项即可。

### 2. 设置客户端

* 前往 [Tailscale 下载页面](https://tailscale.com/download)，并在运行 SillyTavern 的设备以及你想从远程位置使用的设备上下载客户端/应用。
* 在两台设备上使用你之前创建的账户登录。
* 前往 [Tailscale 管理页面](https://login.tailscale.com/admin/machines)并批准两台设备。
* 记下两台已连接设备的名称。

### 3. 将你的设备添加到白名单

* 按照[管理白名单 IP](/usage/remoteconnections/#whitelist-based-access-control) 中的说明，将你连接设备的机器名称（你想用来使用 SillyTavern 的设备）添加到 SillyTavern 的白名单中。

**注意：** 在编辑配置时，如果你没有参考[远程连接](/usage/remoteconnections/#allowing-remote-connections)，你需要将 listen 设置为 true。

### 4. 连接

现在，每当你想从任何地方使用 SillyTavern 时，你只需：

* 在托管 SillyTavern 的 PC 和想要远程使用它的设备上都开启 Tailscale。
* 在想要连接的设备上打开浏览器，并前往 `http://<运行 st 的 PC 的机器名称>:8000/`

### 5. 与朋友共享 SillyTavern 实例（可选）

* 告诉你的朋友创建他们自己的 Tailscale 账户，并在他们的设备上下载客户端。
* 前往 [Tailscale 管理页面](https://login.tailscale.com/admin/machines)。
* 将鼠标悬停在你托管 SillyTavern 的 PC 上的三点按钮上，然后按“Share...”或按三点按钮并按“Sharing settings...”。
* 取消选中“Allow use as an exit node”（除非你希望你的朋友能够通过你的 PC 路由他们的所有互联网流量）。
* 通过电子邮件发送链接，或将标签页切换为“Copy share link”，按下带有相同文本的大蓝色按钮，并以任何其他方式发送给你的朋友。
* 点击你的共享链接后，你的朋友将在他们的 Tailscale 网络中看到你的 PC 弹出。
* 将你在上一步中用于访问 SillyTavern 的相同链接发送给你的朋友。

**注意：** 这将使你的朋友完全访问你 PC 上本地运行的任何服务，如 SillyTavern、automatic1111 等。只有在你真正信任你的朋友时才这样做。