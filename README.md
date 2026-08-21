# 隐私邮箱地址管理

<p align="center">
  <img src="./docs/images/social-preview.png" alt="隐私邮箱地址管理 — 整理 Apple Hide My Email 地址" width="100%" />
</p>

<p align="center">
  中文 · <a href="./README_EN.md">English</a>
</p>

<p align="center">
  <a href="https://github.com/ferretgeek/hide-my-email-manager/actions/workflows/ci.yml"><img src="https://github.com/ferretgeek/hide-my-email-manager/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://github.com/ferretgeek/hide-my-email-manager/actions/workflows/codeql.yml"><img src="https://github.com/ferretgeek/hide-my-email-manager/actions/workflows/codeql.yml/badge.svg" alt="CodeQL" /></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-287f87" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/License-MIT-5f7f55.svg" alt="License: MIT" />
</p>

> Apple 的「隐藏邮件地址」建多了就记不住哪个给了谁。这个工具帮你把它们整理清楚。

## 为什么会需要它

iCloud+ 的 Hide My Email 很好用：每次注册生成一个随机地址，转发到你真实邮箱。

问题出在半年之后。你有四十个 `quiet-leaf-3f2a@icloud.com` 这样的地址，Apple 的界面里只能一页页翻，没有标签、没有备注、没法批量搜索，也带不走。想知道"当初这个地址是给哪家用的"——不记得了。

这个工具就是那本册子：**导入、打标签、写备注、标状态、搜索、备份。** 地址仍然由你在 Apple 官方界面创建；它只负责让你记得住。

**它不接管你的 Apple 账号。** 不接收 Apple 密码、验证码、Cookie 或令牌，也不调用任何未公开的 Apple 接口。

[部署](./docs/DEPLOYMENT.md) · [隐私与安全](./docs/PRIVACY.md) · [问题反馈](https://github.com/ferretgeek/hide-my-email-manager/issues)

## 界面

<p align="center">
  <img src="./docs/images/dashboard.png" alt="地址列表界面" width="100%" />
</p>

<p align="center">
  <img src="./docs/images/intro.png" alt="入口与产品边界设计" width="100%" />
</p>

## 它能做什么

- **整理，而不接管** — 手动添加，或从 TXT / CSV 批量导入；不代替你在 Apple 那边登录和创建地址。
- **默认守住边界** — 地址默认遮罩显示；完整导出必须输入精确确认短语；访问令牌只在当前页面内存中使用。
- **真能用起来** — 搜索、标签、备注、"使用中 / 休眠"状态、重复过滤、事件记录，以及 CSV / JSON / TXT 导出。
- **本地和服务器都行** — Python 标准库即可运行；同时提供 Docker、systemd 与 HTTPS 反向代理配置。
- **四套全局主题** — 天青、翡翠、晚霞与 `#17191d` 深灰；桌面与移动端完整响应式。

## 边界写清楚

| 它会做 | 它永远不会做 |
| --- | --- |
| 保存你主动提供的地址、标签和备注 | 索取或保存 Apple 账号密码、2FA、Cookie、会话或信任令牌 |
| 在本地数据库中标记「使用中 / 休眠」 | 更改 Apple 端状态、自动创建地址或绕过平台限制 |
| 通过官方支持页面引导你完成 Apple 侧操作 | 复刻 Apple 私有网页认证或内部 API |
| 默认生成遮罩导出，完整导出要求显式确认 | 把地址、数据库或令牌上传给第三方 |

Apple 官方的创建与管理步骤见 [Apple Support](https://support.apple.com/guide/icloud/create-and-edit-addresses-mm1a876f7aed/icloud)。

## 三分钟本地运行

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

终端会显示一个带 `#token=...` 的本地地址。**URL fragment 不会发送给服务器**；前端读到之后立即从地址栏移除，并且不写入 `localStorage` 或 `sessionStorage`。

想先看合成数据：

```bash
veil-garden --demo
```

演示只使用 `example.invalid` 保留域名，不接触任何真实地址。

## 导入格式

最简单的 TXT 是每行一个地址；也可以加上你自己起的名字和标签：

```text
quiet.leaf@example.com
paper.lantern@example.com | 阅读订阅 | 阅读,每周
```

服务器端每次最多接收 5000 条记录和 256 KiB 请求体；地址去重不区分大小写。状态、标签和备注只存在本地，**不会同步到 Apple。**

## 服务器部署

公网访问必须放在 HTTPS 反向代理之后，并配置至少 24 字符的强访问令牌与精确的 Host 白名单。

```bash
cp .env.example .env
python -m veil_garden token
docker compose up -d --build
```

把生成的值写入 `.env` 的 `VEIL_ACCESS_TOKEN`，再按[部署指南](./docs/DEPLOYMENT.md)配置 SSH 隧道或 HTTPS。不要把 `.env`、`data/`、SQLite 数据库或导出文件提交进仓库。

## 技术上值得一提的地方

**访问令牌走 URL fragment。** 令牌放在 `#` 之后，浏览器不会把 fragment 发给服务器——所以它不会出现在反向代理和访问日志里。前端读取后立刻从地址栏移除，也不写进任何浏览器存储。

**导入是有上限的。** 每次请求最多 5000 条记录、256 KiB 请求体。一个"批量导入"入口如果没有上限，就等于一个拒绝服务入口。

**完整导出要输确认短语。** 默认导出是遮罩版本。要拿到明文地址清单，必须逐次输入精确短语——因为那份文件本身就是一份高价值目标。

**数据库不是保险箱，而且文档里明说了。** 正式模式使用 `data/veil-garden.sqlite3`，里面包含完整地址和备注。**它不是加密保险箱。** 请限制文件权限，并对磁盘或备份启用加密。把这句话写在 README 里，比假装它安全要负责得多。

**只用标准库。** 运行时代码只使用 Python 标准库，浏览器界面用原生 HTML / CSS / JavaScript，没有第三方运行时资源。

## 它不做什么

- 不登录 Apple、不创建地址、不改动 Apple 端的任何状态。
- 「休眠」和「移除」**只改变本地记录**。要在 Apple 端停用、恢复或删除地址，请用 Apple 官方界面。
- 没有遥测、广告、云同步或第三方运行时资源。

## 开发与验证

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
bandit -r src -ll
```

发布门禁还包含 pip-audit、detect-secrets、Gitleaks（当前文件与完整历史）、干净克隆、Wheel 安装、真实桌面 / 移动端渲染、图片元数据和公开 GitHub 设置复核。详见[发布审计](./docs/发布审计.md)。

## 更多文档

[部署](./docs/DEPLOYMENT.md) · [架构](./docs/ARCHITECTURE.md) · [隐私与安全](./docs/PRIVACY.md) · [发布审计](./docs/发布审计.md) · [版本变更](./CHANGELOG.md) · [参与开发](./CONTRIBUTING.md) · [安全策略](./SECURITY.md)

## 许可与声明

原创代码以 [MIT License](./LICENSE) 发布。

Apple、iCloud、iCloud+、Hide My Email 及相关标识属于各自权利人；本许可证不授予任何第三方品牌或服务的权利。这是独立的非官方社区工具，与 Apple 没有隶属、授权或背书关系。
