# 隐私与安全 / Privacy and security

## 数据流 / Data flow

1. 用户在 Apple 官方界面创建或管理 Hide My Email 地址。 / The user creates or manages an address in Apple's official interface.
2. 用户主动把地址、标签、备注和本地状态输入隐私邮箱地址管理。 / The user deliberately enters an address, label, note, and local state in Hide My Email manager.
3. 浏览器通过同源、Bearer 保护的本地 API 与自托管服务通信。 / The browser talks to the self-hosted service through a same-origin, Bearer-protected API.
4. 正式模式写入本地 SQLite；没有云同步、遥测或第三方运行时请求。 / Production mode writes local SQLite; there is no cloud sync, telemetry, or third-party runtime request.

## 明确不收集 / Explicitly excluded

- Apple Account 密码、二步验证码、Cookie、会话令牌、信任令牌和恢复信息。
- Apple Account passwords, verification codes, cookies, session or trust tokens, and recovery data.
- 浏览器历史、设备标识、分析事件、广告标识或远程日志。
- Browser history, device identifiers, analytics events, advertising identifiers, or remote logs.

应用只链接 Apple 官方支持页面，不向该页面传递地址或应用状态。 / The app only links to Apple's official support page and does not send aliases or application state to it.

## 本地敏感数据 / Sensitive local data

SQLite 数据库保存完整地址、标签和备注。地址可以关联用户在不同网站的活动，因此应按密码库导出物同等谨慎对待：限制文件权限、启用磁盘加密、加密备份，并避免把生产数据放入截图、测试或 Issue。

The SQLite database stores complete addresses, labels, and notes. These can correlate a user's activity across services, so protect the database like a password-vault export: restrict permissions, use disk encryption, encrypt backups, and keep production data out of screenshots, tests, and issues.

## Web 防护 / Web controls

- 非回环 HTTP 默认拒绝；服务器部署应使用 SSH 隧道或 HTTPS 反向代理。 / Non-loopback HTTP is denied by default; use an SSH tunnel or HTTPS reverse proxy.
- Bearer token 使用常量时间比较；令牌不会写入浏览器存储。 / The Bearer token uses constant-time comparison and is not written to browser storage.
- Host 精确白名单、Origin/端口校验、`Sec-Fetch-Site`、CSP、请求/响应上限和滑动窗口限流。 / Exact Host allowlist, Origin/port checks, `Sec-Fetch-Site`, CSP, body limits, and sliding-window rate limits.
- 默认遮罩；完整导出与永久移除本地记录都要求精确确认。 / Masking is the default; full export and permanent local removal both require exact confirmation.
- 不设置跨域许可，不使用 Cookie，不把内部异常、数据库路径或地址写入 HTTP 日志。 / No CORS grant, no cookies, and no internal exception, database path, or alias in HTTP logs.

## 威胁边界 / Threat boundary

隐私邮箱地址管理不能保护已经控制主机、浏览器进程、反向代理、备份或访问令牌的攻击者；也不能验证用户导入的地址是否真的由 Apple 生成。它不加密数据库内容本身。

Hide My Email manager cannot protect against an attacker who controls the host, browser process, reverse proxy, backup, or access token. It cannot prove an imported address came from Apple, and it does not encrypt database contents itself.

发现漏洞请使用仓库的 GitHub Private Vulnerability Reporting，不要在公开 Issue 中附生产数据库、地址、令牌或截图。 / Report vulnerabilities through GitHub Private Vulnerability Reporting. Never attach production databases, addresses, tokens, or sensitive screenshots to a public issue.

