# 核算计算逻辑

本文整理当前核算相关任务的计算口径，重点覆盖 BIC 独立任务、动账资金核算任务、通用上传核算任务，以及对账清单里的商家应付余额预聚合表。

## 1. 任务链路边界

上传文件后，`backend/app/services/upload_service.py` 会根据平台和文件类型派生不同任务：

- 通用核算任务：`backend/app/tasks/celery_app.py`，写入 `fin_financial_summaries`，Douyin 动账还会同步源明细。
- 动账资金核算任务：`backend/app/services/transaction_accounting_service.py`，写入 `fin_transaction_*` 相关表。
- BIC 独立任务：`backend/app/services/bic_accounting_service.py`，写入 BIC 明细和源数据。
- 对账清单任务：`backend/app/services/reconciliation_checklist_service.py`，写入对账清单明细和预聚合汇总表。

同一个 Douyin `动账` 或 `bic` 文件可能同时走通用上传处理和独立任务处理。两条链路的落表和统计维度不同，排查数据时需要先确认页面或接口读的是哪条链路。

## 2. BIC 独立任务

入口：`BicAccountingService.create_from_shared_upload` / `execute_task`。

### 2.1 所属年月

任务先按 BIC 文件配置的所属时间列解析上传所属年月，写回 `BicUploadFile.accounting_year/accounting_month`。如果文件为空，任务按成功结束，摘要提示 `空表，没有数据`。

### 2.2 费用项筛选

费用项由 `BIC_INCLUDED_FEE_ITEMS` 控制：

- 当前配置是 `frozenset({})`，表示允许列表为空，所有费用项都纳入计算。
- 如果后续改成非空集合，则只纳入 `费用项 in BIC_INCLUDED_FEE_ITEMS` 的记录。
- 例如要只算质检通过和质检拒绝，可配置为 `frozenset({"质检费(通过)", "质检费(拒绝)"})`。

### 2.3 仓名归一

`QIC仓` 在解析、分组和源数据落库前都会归一：

- 去掉 `(仓)`、`(配)`、`（仓）`、`（配）`。
- 再做首尾空格清理。

因此 `华东仓`、`华东仓(仓)`、`华东仓(配)`、`华东仓（仓）`、`华东仓（配）` 会按同一个仓处理。

### 2.4 明细分组与源数据

BIC 解析后的有效行先按 `动账流水号` 去重：

- 流水号为空的行不参与去重。
- 同一文件内流水号重复时，后出现的行覆盖前面的行。
- 落库时按 `accounting_period + platform_code + transaction_flow_no` 查找已有源数据；如果存在则覆盖源数据字段，否则新增。

明细表按以下维度聚合：

```text
service_provider + normalized_qic_warehouse
```

每个分组写入一条 `BicDetail`，记录行数和 `结算金额` 合计。源数据行写入 `BicSourceRow`，并通过分组维度关联到对应 `BicDetail`。

### 2.5 分区与重跑

BIC 源数据按 `accounting_period` 确保月分区。重跑同一个 BIC 任务时，会删除该任务旧的明细和源数据后重新解析写入。费用项允许列表或仓名归一规则变更后，历史结果不会自动变化，需要重跑受影响任务。

## 3. 动账资金核算任务

入口：`TransactionAccountingService.create_from_shared_upload` / `execute_task`。当前 v1 只支持 Douyin 动账。

### 3.1 文件校验和所属年月

任务读取 Douyin 动账必要表头，并按配置的所属时间列解析上传所属年月，默认口径是 `动账时间`。如果同一文件检测到多个所属年月，会要求按月份拆分后再上传。

业务年月用于结果分组，当前取每行 `动账时间` 的年月；如果 `动账时间` 无法解析，该行命中的规则会按失败处理。

### 3.2 规则匹配

启用的规则来自 `fin_transaction_rules`，按 `priority, id` 排序。规则字段包括：

- `transaction_direction`：必须等于行上的方向字段，默认 `动账方向`。
- `transaction_scene`：为空表示不限场景；非空时必须等于行上的 `动账场景`。
- `match_type` 和 `remark_pattern`：支持 `none`、`exact`、`contains`、`not_contains`。
- `remark_exclude_pattern`：命中排除关键词时规则不生效。
- `amount_field`：取数字段；字段不存在时会回退到 `动账金额`。
- `result_direction`：支持 `original`、`positive`、`negative`、`directional`。

一行动账可以命中多条规则，所有命中的规则都会产生计算结果并进入汇总；不是只取第一条规则。未命中任何规则的行计入未匹配。

### 3.3 金额方向

金额解析会去掉逗号、人民币符号和 `元`。方向处理规则：

- `original`：保留原始金额。
- `positive`：取绝对值。
- `negative`：取负绝对值。
- `directional`：`入账` 为正，其他方向为负。

### 3.4 落表口径

任务不按 Excel 原始行逐条落明细，而是先聚合：

```text
subject_id + category_id + business_year + business_month
```

每个聚合桶写一条 `TransactionDetail` 和一条 `TransactionSummaryRow`。`TransactionDetail.raw_row` 会标记 `明细类型=聚合明细`，并保留原始匹配明细数、核算年月和业务年月。

任务结果状态：

- 没有未匹配行且没有失败行：`success`。
- 存在未匹配行或失败行：`partial_success`。
- 文件或规则加载失败：`failed`。

## 4. 通用上传核算任务

入口：`backend/app/tasks/celery_app.py`。通用任务通过平台 processor 解析文件，按 `groups` upsert 到 `fin_financial_summaries`。

### 4.1 Douyin 动账汇总

Douyin 动账公式在 `DouyinDongzhangStrategy` 中维护。

归属汇总年月：

- 优先取 `下单时间` 的年月。
- 如果没有 `下单时间`，取 `动账时间` 的上一个月。

行级处理逻辑：

- `匹配赔付`：用赔付分类字典匹配标准化后的 `备注`。
- `退款转赔付`：备注包含 `退款转赔付` 时取 `动账金额`，否则 0。
- `返现`：备注包含 `返现` 且 `动账方向=入账` 时取 `动账金额`，否则 0。
- `退货及其他费用`：匹配到赔付分类时取 `动账金额`，否则 0。

汇总字段：

```text
订单实付 = 订单实付应结 - 返现
退款金额 = 退款转赔付 - 订单退款
GMV = 订单实付 - 退款金额
平台其他收入 = 实际平台补贴 + 实际抖音支付补贴 + 实际抖音月付营销补贴 + 实际达人补贴
平台服务费 = -平台服务费
退货及其他费用 = 行级退货及其他费用
达人佣金 = 佣金
招商服务费 = 招商服务费
站外推广费 = 站外推广费
服务商佣金 = 服务商佣金
```

Douyin 动账成功后，还会把原始字段和处理逻辑字段同步到 `fin_douyin_dongzhang_details`。其中 `bic` 和 `insurance_fee` 初始为 0，后续需要由独立 BIC 或运费险逻辑明确回填策略。

### 4.2 通用 BIC 和运费险汇总

通用 processor 里的 Douyin BIC 是简单月度求和：

```text
归属年月 = 业务发生时间年月
bic = sum(结算金额)
分组 = shop + year + month
```

这条链路不按服务商、QIC 仓或动账流水号出 BIC 明细；这些维度属于 BIC 独立任务。

Douyin 运费险也是简单月度求和：

```text
归属年月 = 下单时间年月
insurance_fee = sum(支付保费)
分组 = shop + year + month
```

## 5. 对账清单预聚合

对账清单明细变化后，`ReconciliationChecklistService._rebuild_summaries` 会按受影响账期删除并重建预聚合汇总。

### 5.1 商家应付余额汇总

表：`fin_reconciliation_checklist_payable_balance_summary_rows`。

分组维度：

```text
org_id + accounting_period + merchant_subject_name + receipt_merchant
```

计算字段：

```text
total_user_paid_amount = sum(user_paid_amount)
total_merchant_net_amount = sum(merchant_net_amount)
total_payment_amount = sum(payment_amount)
total_merchant_net_balance = sum(merchant_net_balance)
```

这个表适合做分区表，因为数据天然按账期查询、重建和导出。当前模型已经声明 `postgresql_partition_by = RANGE (accounting_period)`，分区配置使用：

```text
父表: fin_reconciliation_checklist_payable_balance_summary_rows
月分区前缀: fin_rcl_payable_balance_summary_
一级分区: accounting_period RANGE
二级分区: org_id HASH，16 个子分区
```

后续不要再为每个月手工新建普通表，应通过父表和分区服务管理月分区，避免查询、索引和导出逻辑分叉。

### 5.2 其他对账清单汇总

商品维度汇总：

```text
分组 = org_id + accounting_period + receipt_merchant + merchant_subject_name + product_name
product_quantity = sum(product_quantity)
total_user_paid_amount = sum(user_paid_amount)
total_live_commission = sum(live_commission)
total_merchant_net_amount = sum(merchant_net_amount)
```

收款商家维度汇总：

```text
分组 = org_id + accounting_period + merchant_subject_name + live_platform + receipt_merchant
order_count = count(detail.id)
total_user_paid_amount = sum(user_paid_amount)
total_live_commission = sum(live_commission)
total_merchant_net_amount = sum(merchant_net_amount)
```

## 6. 变更检查清单

调整核算口径时，至少同步检查：

- processor 或 service 中的计算逻辑。
- 任务结果摘要字段。
- 明细、源数据和汇总表的重跑/覆盖规则。
- 导出字段和页面展示字段。
- 对应单元测试和历史数据是否需要重跑回填。
