# Douyin 动账核算源明细设计文档

## 概述

为【动账核算】新增 Douyin 动账源明细存储能力。用户重复上传动账文件后，系统按当前文件重新计算汇总表；汇总表页面支持查看原表明细，明细中同时展示原始 Excel 字段和处理逻辑字段。导出汇总明细/汇总报表时，也可以带出这些源明细数据。

本方案不服务【动账资金核算】模块，不接入 `fin_transaction_*` 表和 `/transaction-accounting` 接口。

## 目标

1. 存储 Douyin 动账原始字段 + 处理逻辑字段。
2. 支持文件重复上传：最新上传结果进入当前汇总与当前明细，历史记录软删除保留。
3. 汇总表页面可下钻查看原表明细。
4. 汇总导出时可追加动账源明细 Sheet。
5. 预留 BIC、运费险字段，由后续新逻辑统计/匹配后写入明细和汇总。

---

## 1. 模块边界

### 所属模块

【动账核算】，对应现有通用上传与财务汇总链路：

- 上传文件：`fin_upload_files`
- 处理任务：`fin_processing_tasks`
- 页面汇总表：`fin_financial_summaries`

### 不涉及模块

【动账资金核算】独立模块：

- 不新增 `fin_transaction_*` 源明细表
- 不修改 `TransactionAccountingService` 的导出逻辑
- 不新增 `/api/v1/transaction-accounting/dongzhang-details`

---

## 2. 数据库模型

### 表名

`fin_douyin_dongzhang_details`

### 表定位

该表是 Douyin 动账核算源明细事实表。每条记录对应动账 Excel 的一条原始数据行，并保存这条数据行计算出的处理逻辑字段。

汇总表 `fin_financial_summaries` 继续作为页面汇总数据来源；源明细通过 `summary_id` 关联到汇总表，支持页面下钻。

### 基础字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BigInteger | 主键 |
| `task_id` | BigInteger | 处理任务 ID，关联 `fin_processing_tasks.id` |
| `file_id` | BigInteger | 上传文件 ID，关联 `fin_upload_files.id` |
| `summary_id` | BigInteger, nullable | 汇总表 ID，关联 `fin_financial_summaries.id` |
| `org_id` | BigInteger | 组织 ID |
| `shop_id` | BigInteger | 店铺 ID |
| `source_platform_code` | String(50) | 来源平台编码，固定为 `douyin` |
| `report_platform_code` | String(50) | 报表归集平台编码 |
| `shop_name` | String(500) | 店铺名称 |
| `source_year` | SmallInteger | 文件名年份，即上传数据年月 |
| `source_month` | SmallInteger | 文件名月份，即上传数据年月 |
| `summary_year` | SmallInteger | 汇总年份，来自下单时间，缺失时按动账时间回退 |
| `summary_month` | SmallInteger | 汇总月份，来自下单时间，缺失时按动账时间回退 |
| `period_source` | String(100) | 汇总年月来源：`order_time` / `transaction_time_previous_month` |
| `source_row_number` | Integer | 源文件行号 |
| `is_deleted` | Boolean | 软删除标记 |
| `deleted_at` | DateTime | 软删除时间 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

不保存 `raw_row`。需要展示和导出的字段全部显式建列。

### 原始字段

原始字段按 Douyin 动账文件表头保留。

| 字段 | 类型 | 原始表头 |
|------|------|---------|
| `transaction_time` | DateTime, nullable | 动账时间 |
| `transaction_flow_no` | String(500) | 动帐流水号 |
| `transaction_direction` | String(50) | 动账方向 |
| `transaction_amount` | NUMERIC(14,2) | 动账金额 |
| `transaction_account` | String(500) | 动账账户 |
| `transaction_scene` | String(500) | 动账场景 |
| `billing_type` | String(500) | 计费类型 |
| `sub_order_no` | String(500) | 子订单号 |
| `order_no` | String(500) | 订单号 |
| `after_sale_no` | String(500) | 售后编号 |
| `order_time` | DateTime, nullable | 下单时间 |
| `product_id` | String(500) | 商品ID |
| `product_name` | Text | 商品名称 |
| `author_id` | String(500) | 达人ID |
| `author_name` | String(500) | 达人名称 |
| `order_type` | String(200) | 订单类型 |
| `order_paid_amount_raw` | NUMERIC(14,2) | 订单实付应结 |
| `shipping_fee` | NUMERIC(14,2) | 运费实付 |
| `platform_subsidy_shipping` | NUMERIC(14,2) | 实际平台补贴_运费 |
| `platform_subsidy` | NUMERIC(14,2) | 实际平台补贴 |
| `other_platform_subsidy` | NUMERIC(14,2) | 其他平台补贴 |
| `trade_in_deduction` | NUMERIC(14,2) | 以旧换新抵扣 |
| `gov_subsidy_platform` | NUMERIC(14,2) | 政府补贴平台垫资 |
| `author_subsidy` | NUMERIC(14,2) | 实际达人补贴 |
| `douyin_pay_subsidy` | NUMERIC(14,2) | 实际抖音支付补贴 |
| `douyin_monthly_subsidy` | NUMERIC(14,2) | 实际抖音月付营销补贴 |
| `bank_subsidy` | NUMERIC(14,2) | 银行补贴 |
| `order_refund_raw` | NUMERIC(14,2) | 订单退款 |
| `platform_fee_raw` | NUMERIC(14,2) | 平台服务费 |
| `commission_raw` | NUMERIC(14,2) | 佣金 |
| `provider_commission_raw` | NUMERIC(14,2) | 服务商佣金 |
| `channel_share` | NUMERIC(14,2) | 渠道分成 |
| `merchant_fee_raw` | NUMERIC(14,2) | 招商服务费 |
| `promotion_fee_raw` | NUMERIC(14,2) | 站外推广费 |
| `other_share` | NUMERIC(14,2) | 其他分成 |
| `is_commission_free` | String(50) | 是否免佣 |
| `commission_free_amount` | NUMERIC(14,2) | 免佣金额 |
| `merchant_name` | Text | 商户主体名称 |
| `remark` | Text | 备注 |

### 处理逻辑字段

这些字段用于页面明细、下钻、导出，以及汇总计算追溯。

| 字段 | 类型 | 展示名称 | 计算逻辑 |
|------|------|----------|---------|
| `matched_compensation` | String(500) | 匹配赔付 | 备注按分类字典匹配赔付类目 |
| `refund_to_compensation` | NUMERIC(14,2) | 退款转赔付 | 备注含 `退款转赔付` 时取动账金额，否则 0 |
| `cashback` | NUMERIC(14,2) | 返现 | 备注含 `返现` 且动账方向为 `入账` 时取动账金额，否则 0 |
| `order_paid` | NUMERIC(14,2) | 收 | 订单实付应结 - 返现 |
| `refund_amount` | NUMERIC(14,2) | 退 | 退款转赔付 - 订单退款 |
| `gmv` | NUMERIC(14,2) | 实收GMV | 收 - 退 |
| `platform_income` | NUMERIC(14,2) | 平台其他收入 | 实际平台补贴 + 实际抖音支付补贴 + 实际抖音月付营销补贴 + 实际达人补贴 |
| `platform_fee_positive` | NUMERIC(14,2) | 平台服务费（修改正数） | -平台服务费 |
| `return_cost` | NUMERIC(14,2) | 退货及其他费用 | 匹配到赔付分类时取动账金额，否则 0 |
| `commission_derived` | NUMERIC(14,2) | 达人佣金 | 佣金 |
| `bic` | NUMERIC(14,2) | BIC | 初始为 0，后续由 BIC 新逻辑统计/匹配写入 |
| `insurance_fee` | NUMERIC(14,2) | 运费险 | 初始为 0，后续由运费险新逻辑统计/匹配写入 |

说明：

- `provider_commission_raw` 已作为原始字段保留。如果页面需要展示服务商佣金，直接展示原始字段即可；本次确认的新增处理逻辑字段不再重复增加服务商佣金派生列。
- `bic` 和 `insurance_fee` 是同一张源明细表里的处理字段，但写入逻辑可以晚于动账文件处理。

---

## 3. 汇总关系

### 汇总表

页面汇总表继续使用 `fin_financial_summaries`。

动账源明细按以下维度汇总并写入汇总表：

- `org_id`
- `shop_id`
- `source_platform_code`
- `report_platform_code`
- `source_year`
- `source_month`
- `summary_year`
- `summary_month`

### 下钻关系

`fin_douyin_dongzhang_details.summary_id` 指向 `fin_financial_summaries.id`。

页面点击某条汇总记录的“查看明细”时：

```sql
SELECT *
FROM fin_douyin_dongzhang_details
WHERE summary_id = :summary_id
  AND is_deleted = false
ORDER BY source_row_number ASC;
```

如果后续 BIC/运费险逻辑只按汇总维度统计，不按订单/流水号分摊，需要在写入时明确分配策略：

- 能匹配到源明细行：更新对应明细行的 `bic` / `insurance_fee`
- 只能按汇总维度统计：可按规则分摊到明细行，或只更新汇总表，不进入源明细行

本需求要求导出明细能看到 BIC、运费险字段，因此建议新逻辑优先设计为可匹配到源明细行。

---

## 4. 重复上传策略

重复上传不阻止创建新上传文件和新处理任务。

当 Douyin 动账文件处理成功后，按业务键软删除旧明细，再插入本次新明细：

```text
org_id
source_platform_code
shop_id
source_year
source_month
```

处理流程：

1. 读取本次上传文件。
2. 计算每条源明细的处理逻辑字段。
3. 按 `summary_year / summary_month` 聚合生成汇总值。
4. upsert `fin_financial_summaries`。
5. 软删除同业务键下旧的 `fin_douyin_dongzhang_details` 当前记录。
6. 插入本次源明细，并写入对应 `summary_id`。

### 唯一键建议

有流水号时，用流水号保证当前有效数据不重复：

```sql
CREATE UNIQUE INDEX uq_douyin_dongzhang_detail_flow
ON fin_douyin_dongzhang_details (
    org_id,
    source_platform_code,
    shop_id,
    source_year,
    source_month,
    transaction_flow_no
)
WHERE is_deleted = false AND transaction_flow_no <> '';
```

无流水号时不强制唯一，依赖重复上传时的业务键软删除。

### 查询索引建议

```sql
CREATE INDEX idx_douyin_dongzhang_detail_summary
ON fin_douyin_dongzhang_details (summary_id)
WHERE is_deleted = false;

CREATE INDEX idx_douyin_dongzhang_detail_task
ON fin_douyin_dongzhang_details (task_id);

CREATE INDEX idx_douyin_dongzhang_detail_file
ON fin_douyin_dongzhang_details (file_id);

CREATE INDEX idx_douyin_dongzhang_detail_source_period
ON fin_douyin_dongzhang_details (
    org_id,
    source_platform_code,
    shop_id,
    source_year,
    source_month
)
WHERE is_deleted = false;

CREATE INDEX idx_douyin_dongzhang_detail_summary_period
ON fin_douyin_dongzhang_details (
    org_id,
    source_platform_code,
    shop_id,
    summary_year,
    summary_month
)
WHERE is_deleted = false;
```

---

## 5. 写入流程

### 上传处理

```text
用户上传 Douyin 动账文件
    |
    v
创建 fin_upload_files / fin_processing_tasks
    |
    v
Celery 读取 Excel
    |
    v
逐行计算源明细字段
    |
    v
按 summary_year / summary_month 聚合
    |
    v
upsert fin_financial_summaries
    |
    v
软删除旧源明细，插入新源明细
    |
    v
页面汇总表展示，支持下钻源明细
```

### 处理结果结构

Douyin 动账 processor 建议返回：

```python
{
    "total_rows": 100,
    "success_rows": 100,
    "failed_rows": 0,
    "groups": {
        "店铺|2026|5": {
            "order_paid_amount": Decimal("..."),
            "refund_amount": Decimal("..."),
            "gmv": Decimal("..."),
            "platform_income": Decimal("..."),
            "platform_fee": Decimal("..."),
            "return_cost": Decimal("..."),
            "commission": Decimal("..."),
        }
    },
    "detail_rows": [
        {
            "source_row_number": 2,
            "summary_year": 2026,
            "summary_month": 5,
            "period_source": "order_time",
            "...": "原始字段和处理逻辑字段"
        }
    ],
}
```

`groups` 继续用于写 `fin_financial_summaries`；`detail_rows` 用于写 `fin_douyin_dongzhang_details`。

---

## 6. BIC / 运费险新逻辑

BIC 和运费险字段先在源明细表建列，初始值为 0。

后续新逻辑落地时，建议提供两个独立服务：

- `apply_bic_to_dongzhang_details(...)`
- `apply_insurance_fee_to_dongzhang_details(...)`

输入可以来自 BIC/运费险文件解析结果，输出更新当前有效的 Douyin 动账源明细。

建议匹配优先级：

1. `sub_order_no`
2. `order_no`
3. `transaction_flow_no`
4. 业务确认后的其他匹配键

更新后需要重新聚合对应 `summary_id` 的 `bic` / `insurance_fee`，保证页面汇总和明细导出一致。

---

## 7. API 设计

### 汇总行查看源明细

```http
GET /api/v1/summaries/{summary_id}/dongzhang-details
```

参数：

- `page`
- `page_size`

返回：

- 原始字段
- 处理逻辑字段
- 基础追踪字段

### 源明细导出

```http
GET /api/v1/summaries/{summary_id}/dongzhang-details/export
```

返回单个汇总行对应的源明细 Excel。

### 汇总导出追加源明细 Sheet

现有汇总导出接口保留，新增可选参数：

```http
GET /api/v1/summaries/export?include_dongzhang_details=true
GET /api/v1/summaries/report/export?include_dongzhang_details=true
```

导出结构：

```text
Sheet 1: 财务汇总 / 汇总报表
Sheet 2: 抖音动账源明细
```

Sheet 2 字段顺序：

1. 基础字段：组织、平台、店铺、上传年月、汇总年月、源文件行号
2. 原始 Douyin 动账字段
3. 处理逻辑字段：匹配赔付、退款转赔付、返现、收、退、实收GMV、平台其他收入、平台服务费（修改正数）、退货及其他费用、达人佣金、BIC、运费险

---

## 8. 页面设计

### 汇总表

汇总表保持当前页面结构，新增操作：

- 查看明细
- 导出明细

### 明细弹窗/抽屉

明细表展示：

- 原始字段
- 处理逻辑字段
- 支持分页
- 支持当前页/选中行/全部导出

处理逻辑字段建议固定靠前或固定靠右，方便业务核对。

---

## 9. 实施步骤

1. 新增 Alembic migration：创建 `fin_douyin_dongzhang_details`。
2. 新增 ORM model：`DouyinDongzhangDetail`。
3. 扩展 Douyin 动账 processor：返回 `detail_rows`。
4. 新增明细持久化服务：软删除旧明细、插入本次明细、关联 `summary_id`。
5. 修改通用 Celery 上传任务：Douyin 动账成功汇总后保存源明细。
6. 新增 summary 下钻 API 与导出 API。
7. 汇总导出支持追加 `抖音动账源明细` Sheet。
8. 前端汇总表增加“查看明细”和“导出明细”入口。
9. 后续接入 BIC / 运费险新逻辑，回填明细字段并重算汇总。

---

## 10. 已确认事项

- 只做【动账核算】，不做【动账资金核算】。
- 不保存 `raw_row`。
- 原始字段按文档清单显式建列保存。
- 明细需要保存处理逻辑字段。
- BIC、运费险需要作为处理逻辑字段保留，后续由新逻辑统计/匹配写入。
- 支持重复上传，页面展示当前有效汇总与当前有效明细。
