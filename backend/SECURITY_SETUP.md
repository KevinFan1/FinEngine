# 生产环境安全配置指南

## ⚠️ 部署前必须完成的安全配置

### 1. 更改 SECRET_KEY

**重要性**: 🔴 **严重** - 默认密钥会导致 JWT 令牌可被伪造，攻击者可以冒充任何用户。

**操作步骤**:

```bash
# 1. 生成强随机密钥
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. 将生成的密钥更新到 .env 文件
# 编辑 backend/.env，替换 SECRET_KEY 的值
SECRET_KEY=<生成的随机密钥>
```

### 2. 更改默认管理员密码

**重要性**: 🔴 **严重** - 默认密码 `admin123` 极易被猜测。

**操作步骤**:

```bash
# 方式 1: 修改初始密码（首次部署前）
# 编辑 backend/.env
SUPERADMIN_INIT_PASSWORD=<强密码>

# 方式 2: 部署后立即登录修改（推荐）
# 1. 使用默认密码登录
# 2. 立即通过前端修改密码
# 3. 建议密码策略：至少 12 位，包含大小写字母、数字和特殊字符
```

### 3. 保护敏感配置文件

```bash
# 确保 .env 文件不被提交到版本控制
echo ".env" >> .gitignore

# 设置文件权限（仅所有者可读写）
chmod 600 backend/.env

# 生产环境建议使用密钥管理服务
# - AWS Secrets Manager
# - Azure Key Vault
# - HashiCorp Vault
```

### 4. 配置强密码策略

当前系统**未实现**密码复杂度验证，建议手动遵循以下规则：

- 最少 12 个字符
- 包含大写字母 (A-Z)
- 包含小写字母 (a-z)
- 包含数字 (0-9)
- 包含特殊字符 (!@#$%^&*)
- 不使用常见密码（password, 123456 等）

### 5. 阿里云凭证安全

```bash
# 编辑 backend/.env
ALIYUN_ACCESS_KEY_ID=<你的 AccessKey ID>
ALIYUN_ACCESS_KEY_SECRET=<你的 AccessKey Secret>

# 建议使用 RAM 子账号，仅授予必要权限：
# - OSS 读写权限
# - STS AssumeRole 权限
```

### 6. 数据库连接安全

```bash
# 使用强密码
DATABASE_URL=postgresql+asyncpg://finengine_user:<强密码>@localhost:5432/finengine

# 生产环境建议：
# - 使用专用数据库用户（非 postgres）
# - 限制数据库用户权限
# - 启用 SSL 连接
# - 配置防火墙规则，仅允许应用服务器访问
```

## 安全检查清单

部署前请确认：

- [ ] SECRET_KEY 已更改为强随机值（至少 32 字节）
- [ ] SUPERADMIN_INIT_PASSWORD 已更改或部署后立即修改
- [ ] .env 文件权限设置为 600
- [ ] .env 文件已添加到 .gitignore
- [ ] 数据库使用强密码
- [ ] 阿里云使用 RAM 子账号，权限最小化
- [ ] 所有默认账号密码已修改
- [ ] 生产环境禁用 DEBUG 模式
- [ ] CORS_ORIGINS 仅包含可信域名

## 定期安全维护

- [ ] 每 90 天轮换 SECRET_KEY（需要用户重新登录）
- [ ] 每 90 天轮换数据库密码
- [ ] 每 180 天轮换阿里云 AccessKey
- [ ] 定期审查用户权限
- [ ] 定期检查安全日志

## 应急响应

如果怀疑密钥泄露：

1. **立即**更改 SECRET_KEY
2. **立即**更改数据库密码
3. **立即**更改阿里云 AccessKey
4. 强制所有用户重新登录
5. 审查操作日志，查找异常活动
6. 通知相关人员

## 参考资源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [阿里云 RAM 最佳实践](https://help.aliyun.com/document_detail/28642.html)
