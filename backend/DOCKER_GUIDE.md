# Docker 部署指南

## 快速开始

### 1. 准备环境变量

```bash
cd backend
cp .env.example .env
# 编辑 .env 文件，至少配置以下项：
# - SECRET_KEY (生成新的随机密钥)
# - ALIYUN_ACCESS_KEY_ID
# - ALIYUN_ACCESS_KEY_SECRET
# - ALIYUN_OSS_BUCKET
# - SENTRY_DSN (可选)
```

### 2. 构建并启动服务

```bash
# 启动所有服务（API + Worker + PostgreSQL + Redis）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f api
docker-compose logs -f worker
```

### 3. 初始化数据库

```bash
# 执行数据库迁移
docker-compose exec api uv run migrate-upgrade

# 初始化种子数据
docker-compose exec api uv run seed-all
```

### 4. 访问服务

- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health
- 详细健康检查: http://localhost:8000/api/v1/health/detailed

## 生产环境部署

### 使用外部数据库和 Redis

如果你使用 RDS 和 Redis 云服务，修改 `docker-compose.yml`:

```yaml
services:
  api:
    environment:
      DATABASE_URL: postgresql+asyncpg://user:password@your-rds-host:5432/finengine
      REDIS_URL: redis://your-redis-host:6379/0
      CELERY_REDIS_URL: redis://your-redis-host:6379/1
    # 移除 depends_on 中的 postgres 和 redis

  worker:
    environment:
      DATABASE_URL: postgresql+asyncpg://user:password@your-rds-host:5432/finengine
      REDIS_URL: redis://your-redis-host:6379/0
      CELERY_REDIS_URL: redis://your-redis-host:6379/1
    # 移除 depends_on 中的 postgres 和 redis

# 注释掉 postgres 和 redis 服务
```

或者创建 `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    env_file:
      - .env.production
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs
    restart: always

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    env_file:
      - .env.production
    volumes:
      - ./logs:/app/logs
    restart: always
```

启动生产环境:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 使用 Docker Swarm 或 Kubernetes

#### Docker Swarm

```bash
# 初始化 Swarm
docker swarm init

# 部署服务栈
docker stack deploy -c docker-compose.yml finengine

# 查看服务
docker service ls

# 扩展 worker
docker service scale finengine_worker=3
```

#### Kubernetes

参考 `deploy/kubernetes/` 目录中的配置文件（需要创建）。

## 常用命令

### 服务管理

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose stop

# 重启服务
docker-compose restart api worker

# 停止并删除容器
docker-compose down

# 停止并删除容器和数据卷
docker-compose down -v
```

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f api
docker-compose logs -f worker

# 查看最近 100 行日志
docker-compose logs --tail=100 api
```

### 进入容器

```bash
# 进入 API 容器
docker-compose exec api bash

# 进入 Worker 容器
docker-compose exec worker bash

# 执行命令
docker-compose exec api uv run migrate-current
docker-compose exec worker celery -A app.tasks.celery_app inspect active
```

### 数据库操作

```bash
# 连接数据库
docker-compose exec postgres psql -U finengine -d finengine

# 备份数据库
docker-compose exec postgres pg_dump -U finengine finengine | gzip > backup_$(date +%Y%m%d).sql.gz

# 恢复数据库
gunzip -c backup_20260516.sql.gz | docker-compose exec -T postgres psql -U finengine -d finengine
```

### 更新部署

```bash
# 拉取最新代码
git pull

# 重新构建镜像
docker-compose build

# 重启服务
docker-compose up -d

# 执行数据库迁移
docker-compose exec api uv run migrate-upgrade
```

## 监控和健康检查

### 健康检查端点

- `/health` - 基础健康检查
- `/api/v1/health/detailed` - 详细健康检查（包含数据库和 Redis）
- `/api/v1/health/readiness` - Kubernetes 就绪探针
- `/api/v1/health/liveness` - Kubernetes 存活探针

### 监控 Celery Worker

```bash
# 查看活跃任务
docker-compose exec worker celery -A app.tasks.celery_app inspect active

# 查看已注册任务
docker-compose exec worker celery -A app.tasks.celery_app inspect registered

# 查看统计信息
docker-compose exec worker celery -A app.tasks.celery_app inspect stats
```

## 性能优化

### 调整 Worker 并发

编辑 `.env`:

```env
CELERY_CONCURRENCY=4  # 并发数
CELERY_POOL=prefork   # 使用 prefork 而不是 solo
```

### 调整 API Workers

修改 `docker-compose.yml`:

```yaml
api:
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 资源限制

```yaml
api:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
```

## 故障排查

### API 无法启动

```bash
# 查看日志
docker-compose logs api

# 检查环境变量
docker-compose exec api env | grep DATABASE_URL

# 测试数据库连接
docker-compose exec api python -c "from app.core.database import async_session_factory; import asyncio; asyncio.run(async_session_factory().__anext__())"
```

### Worker 无法连接 Redis

```bash
# 检查 Redis 连接
docker-compose exec worker python -c "import redis; r = redis.from_url('redis://redis:6379/1'); print(r.ping())"
```

### 数据库迁移失败

```bash
# 查看当前迁移版本
docker-compose exec api uv run migrate-current

# 查看迁移历史
docker-compose exec api uv run migrate-history

# 手动执行迁移
docker-compose exec api uv run migrate-upgrade
```

## 安全建议

1. **不要在生产环境使用 docker-compose.yml 中的默认密码**
2. **使用 secrets 管理敏感信息**
3. **限制容器权限**（已使用非 root 用户）
4. **定期更新基础镜像**
5. **使用私有镜像仓库**
6. **配置防火墙规则**
7. **启用 TLS/SSL**

## 备份策略

### 数据库备份

```bash
# 创建定时任务
crontab -e

# 每天凌晨 2 点备份
0 2 * * * docker-compose -f /path/to/docker-compose.yml exec -T postgres pg_dump -U finengine finengine | gzip > /backup/finengine_$(date +\%Y\%m\%d).sql.gz
```

### 日志备份

```bash
# 日志会持久化到 ./logs 目录
# 定期归档旧日志
find ./logs -name "*.log" -mtime +30 -exec gzip {} \;
```

## 参考资源

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [FastAPI 部署指南](https://fastapi.tiangolo.com/deployment/)
- [Celery 部署指南](https://docs.celeryproject.org/en/stable/userguide/deployment.html)
