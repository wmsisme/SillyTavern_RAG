
# 单点登录 (SSO)

> **⚠️ Warning**
>
> 尽管 SSO 有诸多好处，但它是一个配置和维护复杂的系统。如果配置不正确，可能导致未经授权访问你的实例。请确保在启用 SSO 之前正确配置并测试你的设置。如果你不确定安全影响，建议保持 SSO 自动登录禁用，并改用其他身份验证方法。


SSO 允许你创建用户，并使用在你想要保护的站点上呈现的登录门户来保护许多不同的页面。虽然设置起来很复杂，但它是学习 SSO 以及更好地保护你在互联网上的 ST 实例的好方法。

SSO 还可以替代 [HTTP 基本身份验证](/administration/config-yaml/#user-authentication)，作为 [远程连接](/usage/remoteconnections/) 的访问控制机制。

推荐这样做，因为 SSO 比 HTTP 基本身份验证提供更好的安全性和功能。

[**Authelia**](https://www.authelia.com/) 和 [**Authentik**](https://goauthentik.io/) 是可与 SillyTavern 一起使用的开源 SSO 提供商。

## 配置受信任代理

只有来自配置为受信任代理的 IP 地址的请求，才能通过转发必要的标头来对用户进行身份验证。默认情况下，IPv4 和 IPv6 回环地址都受信任。要允许其他 IP 使用 SSO 标头进行身份验证，请将它们添加到你的 [config.yaml](/administration/config-yaml/#sso-auto-login) 文件中的 `sso.trustedProxies` 列表：

> **💡 Tip**
>
> 还支持 CIDR 和通配符表示法来指定多个 IP 或范围，例如 `192.168.0.*` 或 `10.0.0.0/24`。


```yaml
sso:
  trustedProxies:
    - ::1           # IPv6 回环地址 - 默认受信任
    - 127.0.0.1     # IPv4 回环地址 - 默认受信任
    - '192.168.0.1' # 受信任代理的示例 IP 地址
```

## 使用 SSO 登录

如果你的 SSO 提供的用户名与 SillyTavern 用户账户的用户句柄**完全**匹配，你可以通过 SSO 以该用户身份登录 SillyTavern。要启用此功能，请在 [config.yaml](/administration/config-yaml/#sso-auto-login) 文件中更改以下选项之一：

### Authelia

```yaml
sso:
  autheliaAuth: true
```

### Authentik

```yaml
sso:
  authentikAuth: true
```

这两个选项都会增强或替换 [多用户模式](/administration/multi-user/) 设置中内置的 [密码管理](/usage/user-settings/#account-management) 组件。