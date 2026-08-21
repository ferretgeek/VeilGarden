# 部署与运维

隐私邮箱地址管理保存的是可识别用户用途的完整邮件地址。默认只监听 `127.0.0.1`；除非已经配置 HTTPS、强访问令牌和精确 Host 白名单，否则不要向局域网或公网暴露。

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VEIL_BIND_HOST` | `127.0.0.1` | 监听地址 |
| `VEIL_PORT` | `8768` | 监听端口 |
| `VEIL_ACCESS_TOKEN` | 回环模式自动生成 | 至少 24 字符；非回环部署必填 |
| `VEIL_ALLOWED_HOSTS` | 回环主机自动加入 | 逗号分隔的精确浏览器主机名，禁止 `*` |
| `VEIL_DATA_DIR` | `./data` | SQLite 数据目录 |
| `VEIL_ALLOW_PRIVATE_HTTP` | `0` | 仅隔离的 Docker/私网链路可显式设为 `1` |
| `VEIL_DEMO` | `0` | 使用 `example.invalid` 合成数据和内存数据库 |

生成访问令牌：

```bash
veil-garden token
```

不要把令牌写入仓库、命令参数、URL query、截图或代理访问日志。首次本地启动使用的 URL fragment 会在浏览器读取后立即清除。

## 方案 A：本机直接运行

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install .
veil-garden
```

Windows PowerShell 激活命令是 `.\.venv\Scripts\Activate.ps1`。停止服务使用 `Ctrl+C`；数据默认位于 `data/veil-garden.sqlite3`。

## 方案 B：SSH 隧道访问服务器

这是个人服务器最简单、安全的方式：服务仍只监听服务器回环地址。

服务器：

```bash
export VEIL_ACCESS_TOKEN='replace-with-a-strong-random-value'
export VEIL_ALLOWED_HOSTS='localhost,127.0.0.1'
veil-garden
```

本机建立隧道：

```bash
ssh -N -L 8768:127.0.0.1:8768 user@example-host
```

然后访问 `http://127.0.0.1:8768/` 并输入服务器启动令牌。SSH 主机、账号与密钥只保存在用户自己的 SSH 配置中。

## 方案 C：Docker Compose

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

Compose 默认把容器端口只映射到宿主机 `127.0.0.1:8768`，使用只读根文件系统、移除 Linux capabilities、禁止提权并把数据放入命名卷。若由同一 Docker 网络中的反向代理访问，保留 `VEIL_ALLOW_PRIVATE_HTTP=1`，但不要直接发布容器端口。

## 方案 D：systemd + Nginx HTTPS

1. 创建专用用户、代码目录和数据目录：

```bash
sudo useradd --system --home /var/lib/veil-garden --shell /usr/sbin/nologin veil-garden
sudo install -d -o veil-garden -g veil-garden -m 0700 /var/lib/veil-garden
sudo install -d -o veil-garden -g veil-garden -m 0755 /opt/veil-garden
```

2. 在 `/opt/veil-garden` 建立虚拟环境并安装项目，把 [`deploy/veil-garden.service`](../deploy/veil-garden.service) 复制到 `/etc/systemd/system/`。

3. 创建仅 root 可读的 `/etc/veil-garden.env`：

```ini
VEIL_BIND_HOST=127.0.0.1
VEIL_PORT=8768
VEIL_ACCESS_TOKEN=replace-with-a-strong-random-value
VEIL_ALLOWED_HOSTS=garden.example.com
VEIL_DATA_DIR=/var/lib/veil-garden
```

```bash
sudo chmod 0600 /etc/veil-garden.env
sudo systemctl daemon-reload
sudo systemctl enable --now veil-garden
sudo systemctl status veil-garden
```

4. 复制 [`deploy/nginx.conf.example`](../deploy/nginx.conf.example)，替换示例域名并通过 Certbot 或现有证书配置 TLS。应用不相信客户端提供的转发身份，也不启用 CORS；Nginx 必须保留原始 `Host` 与 `Origin`。

## 健康检查与备份

无需令牌的最小健康端点：

```bash
curl --fail http://127.0.0.1:8768/health
```

备份前停止服务或使用 SQLite 在线备份工具。备份中包含完整地址与备注，必须加密、限制访问并测试恢复。不要把数据库直接复制到公开 Issue、CI artifact 或云盘共享链接。

## 更新与回滚

```bash
git pull --ff-only
source .venv/bin/activate
python -m pip install .
python -m unittest discover -s tests
sudo systemctl restart veil-garden
curl --fail http://127.0.0.1:8768/health
```

更新前复制加密数据库备份并记录当前 Git 标签。回滚时切回已验证标签、重新安装并恢复匹配的备份；不要跳过健康检查和浏览器关键路径。

## 恢复、排错与卸载

恢复时先停止写入，验证备份可读和 SQLite 完整性，再替换数据库、恢复服务账号所有权并启动；随后检查 `/health`、登录、搜索、导入和导出。数据库与备份不是加密保险箱，恢复介质仍需处于加密磁盘和最小权限下。

- `401`：重新输入访问令牌；令牌不会持久化到浏览器。
- Host/Origin 拒绝：核对精确 `VEIL_ALLOWED_HOSTS` 和代理保留的原始头，不要启用通配或 CORS。
- 数据目录只读/锁定：检查单一服务实例、目录所有权、剩余空间和 SQLite 临时文件权限。
- 导入被拒绝：使用规定 CSV/JSON 字段、受限大小和真正生成的合成测试数据；不要上传 Apple 凭据或导出账号会话。
- Apple 端状态与本地不一致：本项目只管理本地记录，停用、恢复和删除仍需在 Apple 官方界面完成。

卸载前停止入口流量和服务并验证加密备份。Docker 先 `docker compose down`；命名卷要在明确放弃恢复后单独删除。systemd 应禁用/移除单元、代理站点、代码和环境文件；`/var/lib/veil-garden` 只在确认不再需要完整地址/备注后删除。撤销可能泄露的访问令牌；删除文件不会让已复制的数据库失效。
