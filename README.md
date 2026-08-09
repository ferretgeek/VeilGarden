# 隐邮花园 / Veil Garden — Hide My Email 地址管理

<p align="center">
  <img src="./docs/images/social-preview.png" alt="隐邮花园本地优先 Hide My Email 地址整理工具预览" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/ferretgeek/VeilGarden/actions/workflows/ci.yml"><img src="https://github.com/ferretgeek/VeilGarden/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://github.com/ferretgeek/VeilGarden/actions/workflows/codeql.yml"><img src="https://github.com/ferretgeek/VeilGarden/actions/workflows/codeql.yml/badge.svg" alt="CodeQL" /></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-287f87" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/License-MIT-5f7f55.svg" alt="License: MIT" />
</p>

> 把替你挡住身份的地址，种进自己的花园。

隐邮花园是一款本地优先的 Hide My Email 地址整理工具。地址仍由你在 Apple 官方界面创建；这里负责安全导入、默认遮罩、标签、备注、状态、搜索和可携带备份。它不接收 Apple Account 密码、验证码、Cookie 或令牌，也不调用未公开的 Apple 接口。

[English](./README_EN.md) · [部署](./docs/DEPLOYMENT.md) · [隐私与安全](./docs/PRIVACY.md) · [问题反馈](https://github.com/ferretgeek/VeilGarden/issues)

## 一眼看懂

<p align="center">
  <img src="./docs/images/dashboard.png" alt="隐邮花园地址花圃实际界面" width="100%" />
</p>

<p align="center">
  <img src="./docs/images/intro.png" alt="隐邮花园入口与产品边界设计" width="100%" />
</p>

- **整理而不接管：** 手动添加，或从 TXT / CSV 批量导入；不代替 Apple 登录和创建地址。
- **默认守住边界：** 地址默认遮罩，完整导出必须输入精确确认短语；访问令牌只在当前页面内存中使用。
- **真正可用：** 搜索、标签、备注、使用中/休眠状态、重复过滤、事件记录，以及 CSV / JSON / TXT 导出。
- **本地与服务器：** Python 标准库即可运行；同时提供 Docker、systemd 与 HTTPS 反向代理配置。
- **四套全局主题：** 天青、翡翠、晚霞与 `#17191d` 深灰；桌面与移动端完整响应式。

## 安全边界

| 会做 | 永远不会做 |
| --- | --- |
| 保存用户主动提供的地址、标签和备注 | 索取或保存 Apple Account 密码、2FA、Cookie、会话或信任令牌 |
| 在本地数据库中标记“使用中 / 休眠” | 更改 Apple 端状态、自动创建地址或绕过平台限制 |
| 通过官方支持页面引导用户完成 Apple 侧操作 | 复刻 Apple 私有网页认证或内部 API |
| 默认生成遮罩导出，完整导出要求显式确认 | 把地址、数据库或令牌上传给第三方 |

Apple 官方的创建与管理步骤见 [Apple Support](https://support.apple.com/guide/icloud/create-and-edit-addresses-mm1a876f7aed/icloud)。本项目是独立的非官方社区工具，与 Apple 没有隶属、授权或背书关系。

## 3 分钟本地运行

需要 Python 3.10 或更高版本。

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install .
veil-garden
```

macOS / Linux：

```bash
source .venv/bin/activate
python -m pip install .
veil-garden
```

终端会显示一个带 `#token=...` 的本地地址。URL fragment 不会发送给服务器；前端读取后立即从地址栏移除，并且不写入 `localStorage` 或 `sessionStorage`。

体验合成数据：

```bash
veil-garden --demo
```

演示只使用 `example.invalid` 保留域名，不接触任何真实地址。

## 导入格式

最简单的 TXT 是每行一个地址；也可增加本地名字和标签：

```text
quiet.leaf@example.com
paper.lantern@example.com | 阅读订阅 | 阅读,每周
```

服务器端每次最多接收 5000 条记录和 256 KiB 请求体；地址去重不区分大小写。状态、标签和备注只存在本地，不会同步到 Apple。

## 服务器部署

公网访问必须放在 HTTPS 反向代理之后，并配置至少 24 字符的强访问令牌与精确 Host 白名单。最小 Docker 示例：

```bash
cp .env.example .env
python -m veil_garden token
docker compose up -d --build
```

把生成值写入 `.env` 的 `VEIL_ACCESS_TOKEN`，再按 [部署指南](./docs/DEPLOYMENT.md) 配置 SSH 隧道或 HTTPS。不要把 `.env`、`data/`、SQLite 数据库或导出文件提交进仓库。

## 数据与限制

- 正式模式默认使用 `data/veil-garden.sqlite3`；数据库包含完整地址和备注，**不是加密保险箱**。请限制文件权限并对磁盘或备份启用加密。
- “休眠”和“移除”仅改变本地记录。若要在 Apple 端停用、恢复或删除地址，请使用 Apple 官方界面。
- 本项目没有遥测、广告、云同步或第三方运行时资源。
- 运行时代码只使用 Python 标准库；浏览器界面使用原生 HTML、CSS 与 JavaScript。

## 开发与验证

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
bandit -r src -ll
```

发布门禁还包含 pip-audit、detect-secrets、Gitleaks 当前文件/完整历史、干净克隆、Wheel 安装、真实桌面/移动端渲染、图片元数据和公开 GitHub 设置复核。详见 [发布审计](./docs/发布审计.md)。

## 许可证

原创代码以 [MIT License](./LICENSE) 发布。Apple、iCloud、iCloud+、Hide My Email 及相关标识属于各自权利人；本许可证不授予任何第三方品牌或服务的权利。
