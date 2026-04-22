# 部署 NovelClaw

这个仓库提供的是一个 GitHub 安全公开版，其中 `NovelClaw` 是主要产品路由，而 `Portal` 与 `MultiAgent` 作为围绕它的辅助层存在。

## 主路由结构

- `/` -> `Portal` 公开入口
- `/multiagent/` -> 可选的 `MultiAgent` 辅助工作区
- `/claw/` -> 主 `NovelClaw` 写作工作区

如果你要把这套系统部署到真实服务器上，`/claw/` 应该被视为主要应用路由。

## 仓库已包含的部署参考

- `infra/nginx/novelclaw.current.conf`
- `infra/systemd/novelclaw-portal.service`
- `infra/systemd/novelclaw-multiagent.service`
- `infra/systemd/novelclaw.service`
- `infra/env/auth-portal.env.template`
- `infra/env/multiagent.env.template`
- `infra/env/novelclaw.env.template`

## 推荐服务器目录结构

```text
/opt/novelclaw/
|-- .venv/
`-- apps/
    |-- auth-portal/
    |-- multiagent/
    `-- novelclaw/

/etc/novelclaw/
|-- auth-portal.env
|-- multiagent.env
`-- novelclaw.env
```

当前仓库内置的 `systemd` 单元默认假设：

- 代码位于 `/opt/novelclaw`
- 环境变量文件位于 `/etc/novelclaw`
- Python 虚拟环境位于 `/opt/novelclaw/.venv`

## 推荐部署步骤

### 1. 上传公开安全版项目文件

至少需要上传：

- `apps/`
- `infra/`
- 如果你希望在服务器上保留辅助脚本，可一并上传 `scripts/`
- 如果你希望保留运维说明，也可以上传 `README.md`、`RUN_LOCAL_WEB.md` 和 `DEPLOYMENT.md`

不要上传恢复后的运行数据、本地 `.env` 文件或私有快照。

### 2. 创建 Python 环境

```bash
cd /opt/novelclaw
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip setuptools wheel
./.venv/bin/pip install -r apps/auth-portal/requirements.txt
./.venv/bin/pip install -r apps/multiagent/requirements.txt
./.venv/bin/pip install -r apps/multiagent/local_web_portal/requirements.txt
./.venv/bin/pip install -r apps/novelclaw/requirements.txt
./.venv/bin/pip install -r apps/novelclaw/local_web_portal/requirements.txt
```

### 3. 准备真实环境变量文件

```bash
sudo mkdir -p /etc/novelclaw
sudo cp infra/env/auth-portal.env.template /etc/novelclaw/auth-portal.env
sudo cp infra/env/multiagent.env.template /etc/novelclaw/multiagent.env
sudo cp infra/env/novelclaw.env.template /etc/novelclaw/novelclaw.env
```

复制完成后，请手动填写：

- 真实域名与公开 URL
- session secret 与 encryption key
- 数据库 URL
- API keys 或 provider 配置
- 与部署路由一致的 `APP_BASE_PATH`

### 4. 安装 systemd 服务

```bash
sudo cp infra/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable novelclaw-portal.service
sudo systemctl enable novelclaw-multiagent.service
sudo systemctl enable novelclaw.service
sudo systemctl restart novelclaw-portal.service
sudo systemctl restart novelclaw-multiagent.service
sudo systemctl restart novelclaw.service
```

### 5. 安装并调整 Nginx 路由配置

复制 `infra/nginx/novelclaw.current.conf` 后，请至少修改：

- `server_name`
- 如启用 HTTPS，则配置证书路径
- 你的宿主机所需的其他反向代理细节

当前示例配置已经把：

- `/` 转发到 `8010`
- `/multiagent/` 转发到 `8011`
- `/claw/` 转发到 `8012`

### 6. 重载 Nginx

```bash
sudo systemctl restart nginx
```

## 部署后检查

部署完成后，建议至少确认以下几点：

1. `/` 能正常打开公开入口页面。
2. `/claw/` 能正常打开主 NovelClaw 工作区。
3. `/multiagent/` 只在你希望暴露辅助工作区时才开放。
4. 在 NovelClaw 中保存 API Key、创建 chat session、启动 run 都能正常工作。
5. run 产物已经写入你配置好的目录。

## 重要安全说明

- 所有密钥都应保存在仓库之外。
- 不要提交或上传本地预览阶段生成的 `.env` 文件。
- 不要公开运行数据库、恢复后的快照或本地密钥材料。
- 仓库中的 env 模板只是占位符，不包含任何可直接用于生产的真实值。
