# 生产环境部署检查清单

## 部署前检查（必须完成）

### 安全配置

- [ ] **SECRET_KEY 已更改**为强随机值（至少 32 字节）
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- [ ] **SUPERADMIN_INIT_PASSWORD 已更改**或计划首次登录后立即修改
- [ ] **数据库密码**使用强密码（至少 16 位，包含大小写字母、数字、特殊字符）
- [ ] **阿里云 AccessKey** 使用 RAM 子账号，权限最小化
- [ ] **.env 文件权限**设置为 600 (`chmod 600 .env`)
- [ ] **.env 文件**已添加到 .gitignore
- [ ] **CORS_ORIGINS** 仅包含可信域名（移除 localhost）
- [ ] **API_CRYPTO_ENABLED** 根据需求配置（建议生产环境启用）

### 数据库配置

- [ ] **RDS 自动备份**已启用（保留 30 天）
- [ ] **跨地域备份**已配置（推荐）
- [ ] **数据库连接池**参数已优化
- [ ] **慢查询日志**已启用
- [ ] **数据库用户权限**最小化（非 root 用户）
- [ ] **SSL 连接**已启用（如果 RDS 支持）

### Redis 配置

- [ ] **Redis 密码**已设置
- [ ] **Redis 持久化**已启用（AOF 或 RDS）
- [ ] **Redis 最大内存**已配置
- [ ] **Redis 淘汰策略**已设置（建议 allkeys-lru）

### 监控和日志

- [ ] **Sentry DSN** 已配置
- [ ] **日志目录**有足够磁盘空间
- [ ] **日志轮转**已配置
- [ ] **健康检查端点**可访问
- [ ] **告警规则**已配置（CPU、内存、磁盘、错误率）

### 性能配置

- [ ] **Celery 并发数**已根据服务器配置调整
- [ ] **API Workers 数量**已优化（建议 2-4 * CPU 核心数）
- [ ] **数据库连接池大小**已配置
- [ ] **文件上传大小限制**已验证

### 网络和防火墙

- [ ] **防火墙规则**已配置（仅开放必要端口）
- [ ] **SSL/TLS 证书**已配置
- [ ] **域名解析**已配置
- [ ] **负载均衡**已配置（如果需要）
- [ ] **CDN**已配置（如果需要）

## 部署步骤

### 1. 准备服务器环境

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker 和 Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 安装其他工具
sudo apt install -y git postgresql-client redis-tools
```

### 2. 克隆代码

```bash
cd /data/www
git clone <repository-url> FinEngine
cd FinEngine/backend
```

### 3. 配置环境变量

```bash
cp .env.example .env
vim .env  # 编辑配置
```

### 4. 构建和启动服务

```bash
# 使用 Docker Compose
docker-compose up -d

# 或使用传统部署
bash deploy/install_backend.sh
bash deploy/init_backend.sh --with-seed
```

### 5. 执行数据库迁移

```bash
docker-compose exec api uv run migrate-upgrade
# 或
uv run migrate-upgrade
```

### 6. 初始化数据

```bash
docker-compose exec api uv run seed-all
# 或
uv run seed-all
```

### 7. 验证部署

```bash
# 检查服务状态
docker-compose ps

# 检查健康状态
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health/detailed

# 检查 Celery Worker
docker-compose exec worker celery -A app.tasks.celery_app inspect active
```

## 部署后验证

### 功能验证

- [ ] **登录功能**正常（使用默认账号或新创建的账号）
- [ ] **验证码生成**正常
- [ ] **文件上传**功能正常
- [ ] **OSS 上传**功能正常
- [ ] **Celery 任务**执行正常
- [ ] **任务列表**显示正常
- [ ] **汇总报表**查询正常
- [ ] **数据导出**功能正常

### 性能验证

- [ ] **API 响应时间** < 500ms（正常请求）
- [ ] **数据库查询时间** < 100ms（简单查询）
- [ ] **文件上传速度**符合预期
- [ ] **并发处理能力**符合预期（压力测试）

### 监控验证

- [ ] **Sentry 错误追踪**正常接收错误
- [ ] **日志文件**正常生成
- [ ] **健康检查**返回正确状态
- [ ] **告警规则**正常触发（测试告警）

### 安全验证

- [ ] **速率限制**生效（登录接口 5 次/分钟）
- [ ] **JWT 令牌**验证正常
- [ ] **权限控制**正常（不同角色访问限制）
- [ ] **SQL 注入**防护有效（测试）
- [ ] **XSS 防护**有效（测试）

## 首次登录后必做

- [ ] **修改默认管理员密码**
- [ ] **创建组织管理员账号**
- [ ] **配置店铺信息**
- [ ] **配置平台信息**
- [ ] **测试完整业务流程**

## 定期维护任务

### 每日

- [ ] 检查服务运行状态
- [ ] 检查错误日志
- [ ] 检查磁盘空间

### 每周

- [ ] 检查数据库备份
- [ ] 检查系统性能指标
- [ ] 检查安全日志

### 每月

- [ ] 测试备份恢复
- [ ] 更新依赖包（安全补丁）
- [ ] 审查用户权限
- [ ] 清理旧日志和临时文件

### 每季度

- [ ] 完整灾难恢复演练
- [ ] 性能优化评估
- [ ] 安全审计
- [ ] 容量规划评估

## 应急响应

### 服务不可用

1. 检查服务状态: `docker-compose ps` 或 `supervisorctl status`
2. 查看错误日志: `docker-compose logs -f api worker`
3. 检查数据库连接: `psql -h <host> -U <user> -d finengine`
4. 检查 Redis 连接: `redis-cli -h <host> ping`
5. 重启服务: `docker-compose restart` 或 `supervisorctl restart finengine:*`

### 数据库问题

1. 检查连接数: `SELECT count(*) FROM pg_stat_activity;`
2. 检查慢查询: 查看 RDS 控制台
3. 检查锁等待: `SELECT * FROM pg_locks WHERE NOT granted;`
4. 如需恢复: 参考 `BACKUP_GUIDE.md`

### Celery 任务堆积

1. 检查 Worker 状态: `celery -A app.tasks.celery_app inspect active`
2. 检查队列长度: `redis-cli llen celery`
3. 增加 Worker 数量: `docker-compose scale worker=3`
4. 清理失败任务: `celery -A app.tasks.celery_app purge`

### 内存/磁盘不足

1. 清理日志: `find logs -name "*.log" -mtime +7 -delete`
2. 清理 Docker: `docker system prune -a`
3. 清理数据库: 归档或删除旧数据
4. 扩容服务器

## 回滚计划

### 代码回滚

```bash
# 回滚到上一个版本
git log --oneline -10  # 查看最近提交
git checkout <commit-hash>
docker-compose build
docker-compose up -d
```

### 数据库回滚

```bash
# 回滚迁移
docker-compose exec api uv run migrate-downgrade -1

# 从备份恢复
bash scripts/restore_database.sh /backup/finengine_20260516.sql.gz
```

## 联系方式

- **技术负责人**: [姓名] [电话] [邮箱]
- **运维负责人**: [姓名] [电话] [邮箱]
- **紧急联系人**: [姓名] [电话] [邮箱]

## 参考文档

- [安全配置指南](SECURITY_SETUP.md)
- [备份指南](BACKUP_GUIDE.md)
- [Docker 部署指南](DOCKER_GUIDE.md)
- [生产环境就绪性评估报告](../生产环境就绪性评估报告.md)

---

**最后更新**: 2026-05-16  
**版本**: 1.0
