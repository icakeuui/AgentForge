# AgentForge Docker 测试部署

这是团队教学和测试交付版本，不代表已完成正式公网生产部署。Compose 启动前端、FastAPI、Redis、Qdrant，使用独立 SQLite 数据卷；不会自动导入已有本地数据库、上传文件或向量库。以下命令均在仓库根目录执行，使用固定项目名 `agentforge`。

## 准备环境和代码

Windows：安装并启动 [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/)，选择 Linux 容器模式，按提示安装 WSL 2。Linux：按 [Docker Engine 官方指南](https://docs.docker.com/engine/install/)安装 Engine 和 Compose 插件并启动服务。确认当前用户有权限使用 Docker，执行 `docker version` 和 `docker compose version`。安装 Git 后在 PowerShell 或 Linux 终端执行：

```sh
git clone https://github.com/icakeuui/AgentForge.git
cd AgentForge
```

首次构建需要访问 Docker Hub、npm 和 Python 包索引，首次使用 BGE 还需要下载模型。请预留足够磁盘空间和时间。

## 配置环境变量

Windows PowerShell：

```powershell
Copy-Item .env.docker.example .env.docker
```

Linux：

```sh
cp .env.docker.example .env.docker
chmod 600 .env.docker
```

编辑 `.env.docker`，分别为 `JWT_SECRET` 和 `AGENT_CONFIG_SECRET` 设置不同的、至少 32 字节的随机密钥。可运行两次 `python -c "import secrets; print(secrets.token_urlsafe(48))"` 来生成。重启、升级及恢复时必须保留原密钥，否则已有令牌或加密配置可能无法使用。不要提交或公开该文件。

按实际服务填写 SMTP 主机、端口、账号、授权码、发件地址和 TLS/SSL；两种加密方式不要同时启用。聊天模型填写 `OPENROUTER_API_KEY`、`OPENROUTER_BASE_URL`、`OPENROUTER_MODEL`。本地 BGE 与聊天模型独立：在智能体中选择 `bge_local`，模型名为 `BAAI/bge-large-zh-v1.5`，无需 Embedding API Key。

## 构建和启动

Windows 与 Linux 均执行：

```sh
docker compose -p agentforge --env-file .env.docker config --quiet
docker compose -p agentforge --env-file .env.docker up -d --build
docker compose -p agentforge --env-file .env.docker ps
```

浏览器访问 `http://localhost:8080`，后端健康检查为 `http://localhost:8080/api/v1/health`。可在 `.env.docker` 修改 `APP_PORT` 并重新执行 `up -d`。默认头像地址由请求生成；反向代理下如有问题，可设置 `AVATAR_PUBLIC_BASE_URL` 为浏览器可访问的完整目录 URL，例如 `https://example.com/uploads/avatars`，再重新执行 `up -d`。

首次加载 BGE 会下载权重并缓存，CPU 推理可能较慢。语音输入需要浏览器支持和麦克风权限，远程访问通常需要 HTTPS。

## 状态、日志和故障排查

```sh
docker compose -p agentforge --env-file .env.docker ps
docker compose -p agentforge --env-file .env.docker logs --tail 100 backend
docker compose -p agentforge --env-file .env.docker logs --tail 100 frontend redis qdrant
docker compose -p agentforge --env-file .env.docker stop
docker compose -p agentforge --env-file .env.docker up -d
```

页面打不开时检查状态、端口占用和前端日志；健康检查失败时检查后端、Redis 和 Qdrant。构建下载超时应检查 Docker 网络和代理；邮件或模型失败时检查对应配置与网络。分享日志前移除密钥及用户内容。

`stop` 保留容器和数据卷，`up -d` 可重新启动；重建容器时数据依赖卷保留。不要使用 `docker compose down -v` 或删除卷来重启服务。

## 持久化、备份和迁移

固定项目名 `agentforge` 下的卷为：`agentforge_agentforge_data`（SQLite）、`agentforge_agentforge_uploads`（头像及上传文件）、`agentforge_agentforge_qdrant`（向量）、`agentforge_agentforge_redis`、`agentforge_agentforge_models`（BGE 缓存）和 `agentforge_agentforge_sessions`（公开会话临时附件）。SQLite 位于 `/app/data/agentforge.db`。会话附件按有效期清理，模型缓存可重新下载。

备份前先停止服务，保证数据库、上传文件、Qdrant 和 Redis 的时间点一致；加密保存备份，并安全保存对应密钥。下面逐卷打包，确保备份磁盘空间足够。

Windows PowerShell：

```powershell
docker compose -p agentforge --env-file .env.docker stop
New-Item -ItemType Directory -Force backups | Out-Null
$backupPath = (Resolve-Path backups).Path
foreach ($name in @('data','uploads','qdrant','redis','models','sessions')) {
  docker run --rm --mount "type=volume,src=agentforge_agentforge_$name,dst=/data,readonly" --mount "type=bind,src=$backupPath,dst=/backup" python:3.12-slim tar -czf "/backup/$name.tar.gz" -C /data .
  if ($LASTEXITCODE -ne 0) { throw "Backup failed: $name" }
}
docker compose -p agentforge --env-file .env.docker up -d
```

Linux：

```sh
docker compose -p agentforge --env-file .env.docker stop
mkdir -p backups
for name in data uploads qdrant redis models sessions; do
  docker run --rm --mount "type=volume,src=agentforge_agentforge_$name,dst=/data,readonly" --mount "type=bind,src=$(pwd)/backups,dst=/backup" python:3.12-slim tar -czf "/backup/$name.tar.gz" -C /data . || exit 1
done
docker compose -p agentforge --env-file .env.docker up -d
```

迁移时使用相同版本、项目名和密钥，在新机器创建空卷、保持服务停止，将每个归档解压到对应空卷后启动并验证账号、文档和检索。先进行独立恢复演练，不要在已有卷上直接覆盖。旧版 Qdrant 数据迁移前须备份并确认官方升级路径，不能随意降级或跨版本覆盖。

## 验收状态与限制

- 已在独立测试环境验证前后端启动、注册登录、智能体创建、DOCX 解析、本地 BGE 生成 1024 维向量、Qdrant 向量检索、公开会话与附件上传，以及重启后测试数据保留。Docker 后端 Qdrant 客户端为 1.12.1，服务端为 1.12.6。
- 聊天模型生成回答仍需验证，公开附件参与模型回答尚未通过验收，真实 SMTP 邮件发送尚未测试。
- npm 审计仍有 7 项中危告警，主要位于开发工具链；告警会随时间变化。
- 正式公网部署需要补充访问控制、安全配置、域名 HTTPS、密钥管理、监控、定期数据备份和恢复演练。SQLite 方案面向单机单后端实例。后端启动会执行已有建表和兼容字段更新，部署到已有数据前须先备份。
