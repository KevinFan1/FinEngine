#!/bin/bash
# PostgreSQL 数据库备份脚本
# 用途: 每日自动备份 FinEngine 数据库

set -e

# 配置
DB_NAME="finengine"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"
BACKUP_DIR="/data/backups/finengine"
RETENTION_DAYS=30

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 生成备份文件名（包含时间戳）
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/finengine_${TIMESTAMP}.sql.gz"

# 执行备份
echo "[$(date)] 开始备份数据库: $DB_NAME"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --no-owner --no-acl --clean --if-exists \
    | gzip > "$BACKUP_FILE"

# 检查备份是否成功
if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "[$(date)] 备份成功: $BACKUP_FILE (大小: $BACKUP_SIZE)"
else
    echo "[$(date)] 备份失败!" >&2
    exit 1
fi

# 清理旧备份（保留最近 N 天）
echo "[$(date)] 清理 ${RETENTION_DAYS} 天前的旧备份..."
find "$BACKUP_DIR" -name "finengine_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete

# 列出当前所有备份
echo "[$(date)] 当前备份列表:"
ls -lh "$BACKUP_DIR"/finengine_*.sql.gz | tail -5

echo "[$(date)] 备份任务完成"
