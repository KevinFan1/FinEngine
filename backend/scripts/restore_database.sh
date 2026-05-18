#!/bin/bash
# 数据库恢复脚本
# 用途: 从备份文件恢复 FinEngine 数据库

set -e

# 配置
DB_NAME="finengine"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"

# 检查参数
if [ $# -eq 0 ]; then
    echo "用法: $0 <备份文件路径>"
    echo "示例: $0 /data/backups/finengine/finengine_20260516_020000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

# 检查备份文件是否存在
if [ ! -f "$BACKUP_FILE" ]; then
    echo "错误: 备份文件不存在: $BACKUP_FILE" >&2
    exit 1
fi

# 确认操作
echo "⚠️  警告: 此操作将覆盖当前数据库 '$DB_NAME'"
echo "备份文件: $BACKUP_FILE"
read -p "确认继续? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "操作已取消"
    exit 0
fi

# 执行恢复
echo "[$(date)] 开始恢复数据库: $DB_NAME"
echo "[$(date)] 从备份文件: $BACKUP_FILE"

# 解压并恢复
gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"

if [ $? -eq 0 ]; then
    echo "[$(date)] 恢复成功!"
else
    echo "[$(date)] 恢复失败!" >&2
    exit 1
fi
