
# 管理

> **⚠️ Warning**
>
> 尽管遵循了许多安全最佳实践，SillyTavern 服务器仍然不够安全，不适合暴露在公共互联网上。
>
> **在未确保采取适当安全措施之前，切勿将任何实例托管在开放互联网上。**
>
> **对于因安全实施不当或不足而导致未经授权访问所造成的任何损害或损失，我们概不负责。**


> **[config.yaml](/administration/config-yaml/)**
>
> SillyTavern 的主配置文件。它包含各种设置，例如网络、安全和后端特定选项。
> > **📝 提示**
>

**[多用户](/administration/multi-user/)**

要与他人共享您的 SillyTavern 实例，您可以创建多个用户账户。每个用户都有自己的设置、扩展和数据。用户账户也可以设置密码保护。
> **📝 提示**

> **[远程访问](/usage/remoteconnections/)**
>
> 您可以从手机、平板电脑或另一台计算机访问您的 SillyTavern 实例。
> > **📝 提示**
>

**[VPN 与隧道](/administration/tunneling/)**

要从互联网访问您的 SillyTavern 实例，您可以使用 VPN 或隧道服务，例如 Cloudflare Zero Trust、ngrok 或 Tailscale。
> **📝 提示**

> **[反向代理](/usage/st-reverse-proxy-guide/)**
>
> 爱好者可以设置反向代理，以便从互联网访问他们的 SillyTavern 实例。
> > **📝 提示**
>
> ## 数据布局
>
> 本节概述了 SillyTavern 中的用户数据存储结构。此处仅描述默认数据布局（数据根目录是 SillyTavern 安装目录的子目录）。如果您已自定义数据布局，请参阅您的自定义配置以了解详情。
>
> ### `data/[user-handle]`（例如 `data/default-user`）
>
> 此文件夹为每个用户账户创建，包含用户特定的数据，例如角色文件、对话历史和设置。
>
> ### `data/_cache`
>
> 用于存储服务器下载的文件的存储位置，例如分词器文件和 transformers.js 模型。
>
> #### `data/_cache/characters`
>
> 当启用 `performance.useDiskCache` 设置时，包含解析后的角色数据，并在启动时以及角色更新时同步。
>
> 这可以加快角色数据的加载速度，但会占用磁盘空间。
>
> ### `data/_css`
>
> 用于存储自定义 CSS 文件的存储位置。
>
> 目前仅支持 `user.css` 文件，它允许您向前端添加自定义样式。
>
> ### `data/_errors`
>
> 用于存储包含各种 HTTP 状态码错误页面的 HTML 文件的存储位置。当服务器遇到错误时，这些文件用于显示自定义错误页面。
>
> - `forbidden-by-whitelist.html`：当请求被 IP 地址白名单阻止时显示。
> - `host-not-allowed.html`：当请求被主机白名单阻止时显示。
> - `unauthorized.html`：当基本身份验证失败时显示。
> - `url-not-found.html`：当请求的资源未找到时显示。
>
> ### `data/_storage`
>
> 用于存储[用户账户数据](/administration/multi-user/)的存储位置。
>
> 不建议手动编辑这些文件，这可能导致数据损坏。
>
> ### `data/_uploads`
>
> 用于临时存储用户上传文件的存储位置，这些文件正在由服务器处理。
>
> 这些文件会在每次启动时自动清除。
>
> ### `data/_webpack`
>
> 用于存储编译后的 webpack 资源和缓存文件的存储位置。
>
> 如果您在更新后遇到前端问题，请尝试清除此文件夹，以强制完全重新构建前端资源。
>
> ### `data/access.log`
>
> 一个日志文件，记录在首次成功连接后传入服务器的 HTTP 请求。
>
> 请定期检查此文件，以监控任何可疑活动。
>
> ### `data/cookie-secret.txt`
>
> 包含服务器中用于签名 cookie 的密钥。
>
> 如果此文件不存在，它会在首次启动时自动生成。
>
> ## 安全检查清单
>
> **这些只是建议。在将您的 ST 实例上线之前，请咨询 Web 应用程序安全专家。**
>
> 1. 保持您的操作系统和运行时软件（例如 Node.js）为最新版本。这可确保您的系统拥有最新的安全补丁和修复，有助于防止潜在漏洞。
> 2. 使用[白名单](/administration/config-yaml/#ip-whitelisting)和网络防火墙。仅允许受信任的 IP 范围访问服务器。
> 3. 启用[基本身份验证](/administration/config-yaml/#user-authentication)。它充当访问前端应用之前的“主密码”。
> 4. 或者，配置外部身份验证。一些已知的服务包括 [Authelia](https://www.authelia.com/) 和 [authentik](https://goauthentik.io/)。详情请参阅 [SSO 指南](/administration/sso/)。
> 5. 切勿让管理员账户没有密码。如果您有任何未受保护的管理员账户，服务器将在启动时向您发出警告。
> 6. 在本地网络之外使用隐蔽登录设置。这会向潜在外部人员隐藏用户列表。
> 7. 经常检查访问日志。它们会写入服务器控制台和 `access.log` 文件，并提供有关传入连接的信息，例如 IP 地址和用户代理。
> 8. 配置 HTTPS。对于 localhost 服务器，您可以生成并使用自签名证书。否则，您可能需要部署反向代理 Web 服务器，例如 [Traefik](https://traefik.io/) 或 [Caddy](https://caddyserver.com/docs/getting-started)。
> 9. 配置并启用[主机白名单](/administration/config-yaml/#host-whitelisting)，尤其是在本地网络上未使用 HTTPS 加密时。
> 10. 配置并启用[私有地址白名单](/administration/config-yaml/#private-address-whitelisting)，以防止 SSRF 攻击。
>
> 在以下指南中查找有关安全代理的更多信息：[反向代理 SillyTavern](/usage/st-reverse-proxy-guide/)。