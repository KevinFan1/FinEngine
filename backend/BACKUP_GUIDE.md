# 数据库备份指南（RDS 版本）

## RDS 自动备份配置

由于你使用的是 RDS 数据库，建议优先使用云服务商提供的自动备份功能。

### 阿里云 RDS 备份配置

1. **启用自动备份**
   - 登录阿里云控制台
   - 进入 RDS 实例管理
   - 备份恢复 > 备份设置
   - 配置：
     - 数据备份保留天数：7-30 天（建议 30 天）
     - 日志备份保留天数：7 天
     - 备份时间：选择业务低峰期（如凌晨 2:00-4:00）
     - 备份频率：每天一次

2. **启用跨地域备份**（推荐）
   - 备份恢复 > 跨地域备份
   - 选择备份地域（建议选择不同地域）
   - 保留天数：30 天

3. **定期测试恢复**
   - 每月至少测试一次备份恢复
   - 使用"克隆实例"功能验证备份完整性

## 应用层备份（补充）

虽然 RDS 有自动备份，但仍建议定期导出逻辑备份到 OSS：

### 1. 手动备份到 OSS

```bash
# 安装 ossutil
wget http://gosspublic.alicdn.com/ossutil/1.7.15/ossutil64
chmod +x ossutil64
./ossutil64 config

# 执行备份并上传
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
pg_dump -h <RDS_HOST> -U <USER> -d finengine | gzip > finengine_${TIMESTAMP}.sql.gz
./ossutil64 cp finengine_${TIMESTAMP}.sql.gz oss://your-bucket/backups/
```

### 2. 自动化备份脚本

已创建的备份脚本仍然可用，只需修改连接参数：

```bash
# 编辑 scripts/backup_database.sh
DB_HOST="rm-xxxxx.mysql.rds.aliyuncs.com"  # 你的 RDS 地址
DB_USER="finengine_user"
DB_NAME="finengine"
```

### 3. 配置 Cron 任务

```bash
# 编辑 crontab
crontab -e

# 添加每日凌晨 3:00 备份任务
0 3 * * * /data/www/FinEngine/backend/scripts/backup_database.sh >> /var/log/finengine_backup.log 2>&1
```

## 备份监控

### 1. 检查 RDS 备份状态

```bash
# 使用阿里云 CLI
aliyun rds DescribeBackups --DBInstanceId=<your-instance-id>
```

### 2. 备份告警

在阿里云控制台配置告警规则：
- 备份失败告警
- 备份空间不足告警
- 备份时间过长告警

## 恢复流程

### RDS 备份恢复

1. **按时间点恢复**（推荐）
   - 控制台 > 备份恢复 > 恢复数据
   - 选择恢复时间点
   - 创建新实例或覆盖当前实例

2. **从备份集恢复**
   - 选择具体备份集
   - 恢复到新实例

### 应用层备份恢复

```bash
# 使用提供的恢复脚本
bash scripts/restore_database.sh /path/to/backup.sql.gz
```

## 灾难恢复计划

### RTO/RPO 目标

- **RPO** (Recovery Point Objective): < 1 小时
  - RDS 自动备份 + 日志备份可实现
- **RTO** (Recovery Time Objective): < 4 小时
  - 包括发现问题、决策、执行恢复的时间

### 灾难场景应对

1. **数据误删除**
   - 使用 RDS 按时间点恢复
   - 恢复到误操作前的时间点

2. **数据库损坏**
   - 从最近的备份集恢复
   - 应用日志备份到最新状态

3. **地域级故障**
   - 使用跨地域备份恢复
   - 切换到备用地域

## 备份检查清单

- [ ] RDS 自动备份已启用
- [ ] 备份保留期 ≥ 30 天
- [ ] 跨地域备份已配置
- [ ] 应用层备份脚本已部署
- [ ] Cron 任务已配置
- [ ] 备份监控告警已配置
- [ ] 每月至少测试一次恢复
- [ ] 备份恢复文档已更新
- [ ] 团队成员了解恢复流程

## 注意事项

1. **备份加密**: RDS 支持备份加密，建议启用
2. **备份成本**: 备份会占用存储空间，注意成本控制
3. **网络安全**: 备份文件包含敏感数据，确保传输和存储安全
4. **权限管理**: 限制备份文件访问权限
5. **定期演练**: 每季度进行一次完整的灾难恢复演练
