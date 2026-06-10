# 对账清单页面内人工修改设计

## 背景

当前对账清单已经支持三类文件上传：

- 原始数据
- 发票更新
- 商家更新

其中发票更新和商家更新适合批量导入，但质检或财务在处理少量异常数据时，仍需要先整理 Excel，再上传任务，路径偏重，反馈也偏慢。对于几十条以内、按子订单号定位并修正字段的场景，更适合提供页面内直接查询和保存的能力。

现有系统已经具备：

- 对账清单底表与 `org_id + 子订单号` 的定位能力
- 发票更新与商家更新两条批量更新链路
- 汇总重建逻辑
- 审计日志能力

因此本期应新增两个轻量页面，专门处理“少量人工修订”，并复用既有更新逻辑与汇总逻辑，避免再起一套和上传不一致的规则。

## 目标

- 在“对账清单”菜单下新增两个独立页面：
  - `发票修改`
  - `商家修改`
- 用户可批量粘贴子订单号查询现有底表数据。
- 单次最多支持 `100` 个子订单号。
- 页面查询结果支持直接表格内编辑并保存。
- 发票修改和商家修改的字段规则，与现有“发票更新上传 / 商家更新上传”保持一致。
- 保存后直接生效，不经过异步任务列表。
- 保存成功后自动重建受影响年月汇总。
- 每次保存必须记录审计日志，便于追溯谁在何时修改了哪些订单。

## 非目标

- 不新增新的上传类型。
- 不新增“删除订单”“作废订单”“恢复历史版本”能力。
- 不新增审批流、二次确认流或草稿流。
- 不支持一次性修改超过 `100` 个子订单号。
- 不在本期支持“按收款商家”“按主体名称”等条件筛选后批量改；本期只支持按子订单号定向修改。
- 不新增独立任务记录；页面保存即刻生效。

## 页面结构

新增两个独立路由，挂在 `对账清单` 一级菜单下：

1. `/reconciliation-checklist/invoice-edits`
2. `/reconciliation-checklist/merchant-edits`

推荐前端文件：

1. `frontend/src/views/reconciliation-checklist/invoice-edits.vue`
2. `frontend/src/views/reconciliation-checklist/merchant-edits.vue`
3. 如需复用，可抽取共享组件：
   - `frontend/src/views/reconciliation-checklist/components/SubOrderQueryPanel.vue`
   - `frontend/src/views/reconciliation-checklist/components/ManualEditResultTable.vue`

两个页面的视觉结构保持一致：

1. 页面标题与说明
2. 子订单号批量输入区
3. 查询结果提示区
4. 可编辑表格
5. 底部保存操作区

## 页面流程

两个页面统一走以下三步：

### 1. 输入子订单号

用户可在多行文本框中批量输入子订单号，支持：

- 换行分隔
- 英文逗号分隔
- 中文逗号分隔

前端处理规则：

- 自动 `trim`
- 自动去重
- 忽略空白项
- 去重后数量超过 `100` 时，不允许查询

页面提示示例：

- `已识别 38 个子订单号`
- `单次最多查询 100 个子订单号`

### 2. 查询现有数据

点击“查询”后，后端按当前用户组织权限查询底表。

查询返回结果分两类：

- `matched_items`：存在于底表、允许编辑的记录
- `missing_sub_order_nos`：未找到的子订单号

页面展示规则：

- 如果全部未找到，页面给出明确提示，但不报系统错误。
- 如果部分未找到，允许用户继续编辑命中的记录。
- 未找到的子订单号单独显示为提示列表，不混入可编辑表格。

### 3. 表格内修改并保存

用户在表格内直接修改字段，点击“保存修改”后立即生效。

保存前规则：

- 仅提交当前查询命中的行
- 仅提交页面允许编辑的字段
- 保存前前端进行基础必填与格式校验
- 后端再次做严格校验

保存后规则：

- 后端直接更新底表
- 自动重建受影响年月汇总
- 前端提示成功条数、未命中条数和涉及年月

## 字段设计

### 发票修改页

查询结果表格字段：

1. `序号`
2. `子订单号`（只读）
3. `收款商家`（可编辑）
4. `开票时间`（可编辑）
5. `发票号码`（可编辑）

保存字段与现有“发票更新上传”保持一致：

- `sub_order_no`
- `receipt_merchant`
- `invoice_time`
- `invoice_number`

### 商家修改页

查询结果表格字段：

1. `序号`
2. `子订单号`（只读）
3. `收款商家`（可编辑）
4. `应付商家净额`（可编辑）
5. `付款金额`（可编辑）
6. `付款时间（商家）`（可编辑）

保存字段与现有“商家更新上传”保持一致：

- `sub_order_no`
- `receipt_merchant`
- `merchant_net_amount`
- `payment_amount`
- `merchant_payment_time`

## 查询与保存规则

### 通用规则

- 单次最多 `100` 个子订单号。
- 去重后为空时，不允许查询。
- 仅允许查询当前组织可见数据。
- 子订单号不存在时，不允许保存该行。
- 仅允许更新既有底表记录，不允许页面内创建新底表行。

### 发票修改规则

- `收款商家` 允许为空字符串，表示清空。
- `开票时间` 允许为空，表示清空。
- `发票号码` 允许为空字符串，表示清空。

### 商家修改规则

- `收款商家` 允许为空字符串，表示清空。
- `应付商家净额` 允许为空，保存时按现有上传逻辑处理为 `0.00`。
- `付款金额` 允许为空，表示清空。
- `付款时间（商家）` 允许为空，表示清空。

### 汇总联动规则

保存成功后，必须按命中记录所属 `accounting_period` 重建：

- 商品汇总
- 商家总表汇总
- 商家应付余额明细汇总

若一次保存涉及多个年月，需统一收集后批量重建。

## 接口设计

建议新增 4 个接口，保持职责清晰。

### 1. 发票修改查询

`POST /api/v1/reconciliation-checklist/invoice-edits/query`

请求体：

```json
{
  "org_id": 1,
  "sub_order_nos": ["SO-1", "SO-2"]
}
```

响应体：

```json
{
  "matched_items": [
    {
      "sub_order_no": "SO-1",
      "receipt_merchant": "收款商家A",
      "invoice_time": "2026-06-09 10:00:00",
      "invoice_number": "FP-001"
    }
  ],
  "missing_sub_order_nos": ["SO-2"]
}
```

### 2. 发票修改保存

`POST /api/v1/reconciliation-checklist/invoice-edits/save`

请求体：

```json
{
  "org_id": 1,
  "items": [
    {
      "sub_order_no": "SO-1",
      "receipt_merchant": "收款商家A",
      "invoice_time": "2026-06-09 10:00:00",
      "invoice_number": "FP-001"
    }
  ]
}
```

响应体：

```json
{
  "success_count": 1,
  "failed_count": 0,
  "missing_sub_order_nos": [],
  "affected_periods": [202606]
}
```

### 3. 商家修改查询

`POST /api/v1/reconciliation-checklist/merchant-edits/query`

### 4. 商家修改保存

`POST /api/v1/reconciliation-checklist/merchant-edits/save`

请求与响应结构与发票修改同型，只是字段替换为商家更新字段。

## 后端实现

### API 层

建议新增接口文件中的 schema：

- `ReconciliationChecklistManualQueryIn`
- `ReconciliationChecklistInvoiceEditItemIn`
- `ReconciliationChecklistMerchantEditItemIn`
- `ReconciliationChecklistManualQueryOut`
- `ReconciliationChecklistManualSaveOut`

放在：

`backend/app/schemas/reconciliation_checklist.py`

接口放在：

`backend/app/api/v1/reconciliation_checklist.py`

### Service 层

核心原则：**复用现有上传更新逻辑，不再实现一套平行规则。**

建议新增方法：

- `query_invoice_edit_items`
- `save_invoice_edit_items`
- `query_merchant_edit_items`
- `save_merchant_edit_items`

内部流程：

1. 标准化并去重子订单号
2. 校验最大数量
3. 通过 `order_keys` 和底表查询命中记录
4. 对保存入参做结构转换
5. 复用现有：
   - `_apply_invoice_rows`
   - `_apply_merchant_rows`
6. 收集 `affected_periods`
7. 调用 `_ensure_period_partitions`
8. 调用 `_rebuild_summaries`

这样可以保证：

- 上传修改和页面修改规则一致
- 金额清空逻辑一致
- 未知子订单号处理一致
- 汇总重建行为一致

## 审计日志

必须记录操作日志。

建议审计日志使用：

- `module="reconciliation_checklist"`
- `action="invoice_edit"` 或 `action="merchant_edit"`

描述建议：

- `批量修改对账清单发票信息`
- `批量修改对账清单商家信息`

`extra_data` 建议记录：

- `query_count`
- `save_count`
- `success_count`
- `missing_sub_order_count`
- `sub_order_samples`：前 10 个子订单号样例
- `affected_periods`

日志目标建议：

- `target_type="reconciliation_checklist_manual_edit"`
- `target_id=0`
- `target_name="invoice"` 或 `target_name="merchant"`

## 前端交互细节

### 输入区

- 多行文本框
- 实时显示识别数量
- “清空”按钮
- “查询”按钮

### 表格

- 第一列必须是 `序号`
- 仅命中的行进入表格
- 表格内直接编辑
- 支持单元格空值清空

### 状态反馈

查询后提示：

- `命中 28 条，未找到 3 条`

保存后提示：

- `已成功更新 28 条，涉及 202606、202607`

错误提示要避免直接暴露底层异常，沿用对账清单现有风格。

## 错误处理

前端错误：

- 输入超过 `100` 个子订单号
- 查询时没有有效子订单号
- 保存时没有任何可保存记录

后端错误：

- 子订单号数量超限
- 数据不存在或无权限
- 时间格式非法
- 金额格式非法
- 保存异常

保存异常对前端统一返回友好提示：

`处理异常，请联系管理员或稍后重试`

详细异常仅写日志。

## 测试

### 后端测试

- 查询时子订单号去重生效
- 查询超过 `100` 个时报错
- 未知子订单号返回到 `missing_sub_order_nos`
- 发票修改保存复用现有更新链路
- 商家修改保存复用现有更新链路
- 空值清空覆盖生效
- 保存后汇总重建收到正确的 `affected_periods`
- 审计日志记录正确

### 前端测试 / 验证

- 两个新菜单可见
- 子订单号多行粘贴可正确拆分
- 超过 `100` 个前端拦截
- 查询结果正确区分“命中”和“未找到”
- 表格内编辑后可成功保存
- 第一列显示序号
- 成功和失败提示文案正确

## 推荐实施顺序

1. 新增后端 query/save schema
2. 新增 service 查询与保存方法
3. 新增 4 个 API
4. 补审计日志
5. 新增两个前端页面和路由
6. 跑后端测试与前端构建

## 结论

本方案通过“两个独立页面 + 子订单号批量查询 + 表格内直接修改 + 立即生效”的方式，为质检和财务提供轻量的人工作业入口。

它不替代既有上传，而是补足少量修订场景；同时复用现有发票更新、商家更新和汇总重建逻辑，保证页面修改与上传修改规则一致，并通过审计日志满足追溯要求。
