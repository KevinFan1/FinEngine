# Douyin 动账明细表设计文档

## 概述

为 Douyin 动账处理新增明细存储功能，将原始 Excel 数据和计算派生字段保存到数据库，支持在核算明细和核算报表导出时提供第二个 Sheet。

## 目标

1. 存储 Douyin 动账原始字段 (40个) + 派生字段 (13个)
2. 支持文件重传时的数据去重 (upsert + 软删除)
3. 支持 50 万条数据的批量处理
4. 在导出时提供明细 Sheet

---

## 1. 数据库模型

### 表名

`fin_douyin_dongzhang_details`

### 字段结构

#### 基础字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BigInteger | 主键 |
| `task_id` | BigInteger | 处理任务 ID |
| `file_id` | BigInteger | 上传文件 ID |
| `org_id` | BigInteger | 组织 ID |
| `shop_id` | BigInteger | 店铺 ID |
| `platform_code` | String(50) | 平台编码 (douyin) |
| `shop_name` | String(200) | 店铺名称 |
| `accounting_year` | SmallInteger | 核算年份 |
| `accounting_month` | SmallInteger | 核算月份 |
| `business_year` | SmallInteger | 业务年份 (从下单时间提取) |
| `business_month` | SmallInteger | 业务月份 (从下单时间提取) |
| `source_row_number` | Integer | 源文件行号 |
| `is_deleted` | Boolean | 软删除标记 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

#### 原始字段 (40个)

| 字段 | 类型 | 原始表头 |
|------|------|---------|
| `transaction_time` | String(100) | 动账时间 |
| `transaction_flow_no` | String(200) | 动帐流水号 |
| `transaction_direction` | String(20) | 动账方向 |
| `transaction_amount` | NUMERIC(14,2) | 动账金额 |
| `transaction_account` | String(100) | 动账账户 |
| `transaction_scene` | String(200) | 动账场景 |
| `billing_type` | String(100) | 计费类型 |
| `sub_order_no` | String(100) | 子订单号 |
| `order_no` | String(100) | 订单号 |
| `after_sale_no` | String(100) | 售后编号 |
| `order_time` | String(100) | 下单时间 |
| `product_id` | String(100) | 商品ID |
| `product_name` | String(500) | 商品名称 |
| `达人_id` | String(100) | 达人ID |
| `达人_name` | String(200) | 达人名称 |
| `order_type` | String(100) | 订单类型 |
| `order_paid_amount` | NUMERIC(14,2) | 订单实付应结 |
| `shipping_fee` | NUMERIC(14,2) | 运费实付 |
| `platform_subsidy_shipping` | NUMERIC(14,2) | 实际平台补贴_运费 |
| `platform_subsidy` | NUMERIC(14,2) | 实际平台补贴 |
| `other_platform_subsidy` | NUMERIC(14,2) | 其他平台补贴 |
| `trade_in_deduction` | NUMERIC(14,2) | 以旧换新抵扣 |
| `gov_subsidy_platform` | NUMERIC(14,2) | 政府补贴平台垫资 |
| `达人_subsidy` | NUMERIC(14,2) | 实际达人补贴 |
| `douyin_pay_subsidy` | NUMERIC(14,2) | 实际抖音支付补贴 |
| `douyin_monthly_subsidy` | NUMERIC(14,2) | 实际抖音月付营销补贴 |
| `bank_subsidy` | NUMERIC(14,2) | 银行补贴 |
| `order_refund` | NUMERIC(14,2) | 订单退款 |
| `platform_fee` | NUMERIC(14,2) | 平台服务费 |
| `commission` | NUMERIC(14,2) | 佣金 |
| `provider_commission` | NUMERIC(14,2) | 服务商佣金 |
| `channel_share` | NUMERIC(14,2) | 渠道分成 |
| `merchant_fee` | NUMERIC(14,2) | 招商服务费 |
| `promotion_fee` | NUMERIC(14,2) | 站外推广费 |
| `other_share` | NUMERIC(14,2) | 其他分成 |
| `is_commission_free` | String(20) | 是否免佣 |
| `commission_free_amount` | NUMERIC(14,2) | 免佣金额 |
| `merchant_name` | String(500) | 商户主体名称 |
| `remark` | Text | 备注 |

#### 派生字段 (13个)

| 字段 | 类型 | 计算逻辑 |
|------|------|---------|
| `matched_compensation` | String(200) | 匹配赔付 (通过 classify_text) |
| `refund_to_compensation` | NUMERIC(14,2) | 退款转赔付 (备注含"退款转赔付"时取动账金额) |
| `cashback` | NUMERIC(14,2) | 返现 (备注含"返现"且方向为"入账"时取动账金额) |
| `order_paid` | NUMERIC(14,2) | 收 = 订单实付应结 - 返现 |
| `refund_amount` | NUMERIC(14,2) | 退 = 退款转赔付 - 订单退款 |
| `gmv` | NUMERIC(14,2) | 实收GMV = 收 - 退 |
| `platform_income` | NUMERIC(14,2) | 平台其他收入 = 实际平台补贴 + 实际抖音支付补贴 + 实际抖音月付营销补贴 |
| `platform_fee_positive` | NUMERIC(14,2) | 平台服务费(修改正数) = -平台服务费 |
| `return_cost` | NUMERIC(14,2) | 退货及其他费用 (匹配到赔付分类时取动账金额) |
| `commission_derived` | NUMERIC(14,2) | 达人佣金 = 佣金 |
| `provider_commission_derived` | NUMERIC(14,2) | 服务商佣金 |
| `bic` | NUMERIC(14,2) | BIC |
| `insurance_fee` | NUMERIC(14,2) | 运费险 |

### 索引设计

```sql
-- 主键
PRIMARY KEY (id)

-- 业务唯一键 (用于 upsert 冲突检测)
UNIQUE (org_id, platform_code, shop_id, accounting_year, accounting_month, transaction_flow_no)
WHERE is_deleted = false AND transaction_flow_no <> ''

-- 查询索引
INDEX idx_dongzhang_detail_task ON fin_douyin_dongzhang_details (task_id)
INDEX idx_dongzhang_detail_org_period ON fin_douyin_dongzhang_details (org_id, accounting_year, accounting_month)
INDEX idx_dongzhang_detail_org_shop_period ON fin_douyin_dongzhang_details (org_id, shop_id, accounting_year, accounting_month)
INDEX idx_dongzhang_detail_business_period ON fin_douyin_dongzhang_details (org_id, business_year, business_month)
```

---

## 2. 分区策略

### 主分区: 按核算月份

```sql
CREATE TABLE fin_douyin_dongzhang_details (
    ...
) PARTITION BY RANGE (accounting_year, accounting_month);

-- 月度分区示例
CREATE TABLE fin_douyin_dongzhang_details_202601
    PARTITION OF fin_douyin_dongzhang_details
    FOR VALUES FROM (2026, 1) TO (2026, 2);
```

### 自动分区维护

```python
def ensure_partition_exists(year: int, month: int):
    """确保分区存在，不存在则创建"""
    table_name = f"fin_douyin_dongzhang_details_{year}{month:02d}"
    if not partition_exists(table_name):
        create_partition(year, month)
```

---

## 3. Upsert + 软删除机制

### 场景处理

| 场景 | 处理方式 |
|------|---------|
| 同文件重传 (file_id 相同) | 软删除旧记录，插入新记录 |
| 不同文件相同流水号 | 更新已有记录 (保留最新数据) |
| 全新数据 | 直接插入 |

### 实现逻辑

```python
async def upsert_dongzhang_details(
    session: AsyncSession,
    task_id: int,
    file_id: int,
    org_id: int,
    records: list[dict],
) -> tuple[int, int]:
    """插入/更新动账明细，返回 (处理数, 删除数)"""
    
    # Step 1: 软删除该文件的所有旧记录 (处理重传)
    delete_result = await session.execute(
        update(DouyinDongzhangDetail)
        .where(
            DouyinDongzhangDetail.file_id == file_id,
            DouyinDongzhangDetail.is_deleted == False,
        )
        .values(is_deleted=True, updated_at=func.now())
    )
    deleted_count = delete_result.rowcount
    
    # Step 2: 批量 upsert (处理不同文件的相同流水号)
    batch_size = 5000
    processed = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        
        stmt = insert(DouyinDongzhangDetail).values(batch)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_dongzhang_business_key",
            set_={
                "task_id": stmt.excluded.task_id,
                "file_id": stmt.excluded.file_id,
                "shop_id": stmt.excluded.shop_id,
                "shop_name": stmt.excluded.shop_name,
                # ... 更新所有字段
                "is_deleted": False,
                "updated_at": func.now(),
            },
        )
        
        await session.execute(stmt)
        processed += len(batch)
    
    await session.commit()
    return processed, deleted_count
```

---

## 4. 性能优化

### 批量处理策略

| 方案 | 适用场景 | 实现方式 |
|------|---------|---------|
| 批量插入 | 标准处理 | 每 5000 条一批 |
| 异步任务 | 大文件 (>10000条) | Celery 后台任务 |
| 进度更新 | 长时间处理 | 更新 task.progress |

### Celery 任务实现

```python
@celery_app.task(bind=True, max_retries=3)
def process_douyin_dongzhang_details(self, task_id: int, file_path: str):
    """异步处理动账明细"""
    try:
        # 1. 读取文件
        rows = read_excel(file_path)
        
        # 2. 分批处理
        batch_size = 5000
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            
            # 3. 计算派生字段
            records = [compute_derived_fields(row) for row in batch]
            
            # 4. Upsert
            processed, deleted = await upsert_dongzhang_details(...)
            
            # 5. 更新进度
            update_task_progress(task_id, i + len(batch), len(rows))
            
    except Exception as e:
        self.retry(exc=e, countdown=60)
```

---

## 5. 导出功能

### 核算明细 (export_details)

```
Sheet 1: 动账汇总明细 (现有)
  - 序号, 月份, 平台, 店铺, 现金流量组, 科目, 类目, 金额

Sheet 2: 动账源明细 (新增)
  - 所有原始字段 + 派生字段
```

### 核算报表 (export_summaries)

```
Sheet 1: 动账汇总报表 (现有)
  - 月份, 平台, 店铺, 收入, 支出, 净利润

Sheet 2: 动账源明细 (新增)
  - 同上
```

### 实现方式

```python
def export_details_with_source(self, ...):
    workbook = Workbook(write_only=True)
    
    # Sheet 1: 汇总明细
    ws1 = workbook.create_sheet(title="动账汇总明细")
    self._write_detail_sheet(ws1, ...)
    
    # Sheet 2: 源明细
    ws2 = workbook.create_sheet(title="动账源明细")
    self._write_source_sheet(ws2, ...)
    
    # 保存
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer
```

---

## 6. API 接口

### 新增接口

```
GET /api/v1/transaction-accounting/dongzhang-details
  - 参数: org_id, shop_id, accounting_year, accounting_month
  - 返回: 明细列表 + 分页

GET /api/v1/transaction-accounting/dongzhang-details/export
  - 参数: 同上
  - 返回: Excel 文件 (两个 Sheet)
```

---

## 7. 数据流程

```
用户上传 Douyin 动账 Excel
    │
    ▼
┌─────────────────────────────────┐
│ 1. 创建 UploadFile 记录         │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 2. 创建 Celery 任务             │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 3. 后台处理                     │
│    - 读取 Excel                 │
│    - 计算派生字段               │
│    - 分批 upsert 到明细表       │
│    - 更新汇总表                 │
│    - 更新任务进度               │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 4. 完成通知                     │
└─────────────────────────────────┘
```

---

## 8. 待确认事项

- [ ] 是否需要支持按业务月份查询？(目前只有核算月份)
- [ ] 是否需要保留历史版本？(当前方案只保留最新)
- [ ] 导出时是否需要支持筛选条件？
