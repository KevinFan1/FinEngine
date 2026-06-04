# 对账清单独立功能设计

## 背景

财务需要一个独立的“对账清单”功能，用于导入模板表中的动账佣金明细，按年月、直播推广方和收款商家汇总，并导出符合附件样式的佣金明细 Excel。

现有系统已经有统一上传中心、OSS 直传、Celery 任务、下载中心、动账资金核算、BIC 核算和旧商家对账模块。本功能应独立建设，不影响旧商家对账的红单、银行流水、匹配、期初金额、净额比例等已有流程。

## 目标

- 新增独立菜单“对账清单”，包含上传、任务、汇总页面。
- 下载空白模板，模板只保留表头。
- 前端上传前校验 Excel 表头，校验通过后直传 OSS。
- 上传完成后创建后端任务，由 Celery 异步解析入库。
- 用 `动账时间` 解析数据年月，并按年月分区保存明细。
- 用 `组织 + 平台 + 店铺 + 年月 + 动账流水号` 作为明细唯一键执行 upsert。
- 如果上传数据中的店铺不存在，按 `平台 + 店铺` 自动新增店铺。
- 汇总按 `年月 + 直播推广方 + 收款商家` 聚合。
- 每条汇总支持查看按 `商品名称` 聚合的明细。
- 支持选择汇总行导出，导出 workbook 按 `年月 + 收款商家 + 直播推广方` 创建 sheet。
- 隐藏旧“商家对账”前端菜单，不删除旧路由、旧接口和旧数据。

## 非目标

- 不改旧商家对账后端逻辑。
- 不迁移或复用旧商家对账红单、银行流水和汇总数据。
- 不把对账清单上传混入旧商家对账页面。
- 不在本期增加人工调整、作废、删除明细或汇总锁账能力。
- 不支持用户自定义模板字段。本期只支持固定 10 列表头。
- 不支持跨平台特殊解析规则。平台字段按表内值保存，店铺按表内平台和店铺名称维护。

## 模板与表头

模板来源文件：

`/Users/kevinfan/Documents/财务需求/对账单需求/对账清单模版.xlsx`

模板中实际表头为：

1. `平台`
2. `店铺`
3. `动账时间`
4. `动帐流水号`
5. `商品名称`
6. `直播推广方`
7. `收款商家`
8. `GMV`
9. `直播推广佣金`
10. `应付商家净额`

下载模板接口返回只有表头的空白 `.xlsx`。上传校验应以这 10 列作为必需字段，并兼容 `动账流水号` 和模板原字 `动帐流水号` 两种写法，入库字段统一为 `transaction_flow_no`。

表头校验规则：

- 第一张非空工作表的第一行必须包含上述 10 个字段。
- 字段顺序建议严格匹配模板；如果实现复用现有上传中心的宽松校验，也必须保证必需字段齐全且没有把别的列误识别为关键字段。
- 前端校验用于快速反馈，后端 Celery 处理时必须再次校验，避免绕过前端造成脏数据。

## 数据模型

新增模型文件建议为 `backend/app/models/reconciliation_checklist.py`。

### 上传文件表

表名：`fin_reconciliation_checklist_files`

用途：记录每次对账清单上传文件和任务结果摘要。

关键字段：

- `id`
- `org_id`
- `user_id`
- `source_upload_file_id`：关联统一上传文件，可空。
- `original_name`
- `oss_key`
- `file_size`
- `file_hash`
- `status`：`uploaded`、`running`、`success`、`failed`。
- `row_count`
- `inserted_rows`
- `updated_rows`
- `failed_rows`
- `error_message`
- `result_summary`
- `created_at`
- `updated_at`
- 软删除字段

### 任务表

表名：`fin_reconciliation_checklist_tasks`

用途：独立展示对账清单处理任务，避免污染旧商家对账任务视图。

关键字段：

- `id`
- `file_id`
- `org_id`
- `user_id`
- `celery_task_id`
- `status`：`queued`、`running`、`success`、`failed`。
- `progress`
- `total_rows`
- `success_rows`
- `failed_rows`
- `inserted_rows`
- `updated_rows`
- `error_message`
- `result_summary`
- `started_at`
- `finished_at`
- `created_at`
- `updated_at`
- 软删除字段

### 明细表

表名：`fin_reconciliation_checklist_details`

用途：保存对账清单每条源明细，按 `accounting_period` 分区。

分区：

- PostgreSQL `RANGE (accounting_period)`。
- 每个导入任务处理到某个年月时，确保该年月分区存在。

关键字段：

- `id`
- `task_id`
- `file_id`
- `org_id`
- `shop_id`
- `platform_code`
- `platform_name`
- `shop_name`
- `accounting_year`
- `accounting_month`
- `accounting_period`
- `source_row_number`
- `transaction_time`
- `transaction_flow_no`
- `product_name`
- `live_promoter`
- `receipt_merchant`
- `gmv`
- `live_commission`
- `merchant_net_amount`
- `raw_row`
- `created_at`
- `updated_at`
- 软删除字段

唯一键：

`org_id + platform_code + shop_id + accounting_period + transaction_flow_no`

唯一键只对未删除且 `transaction_flow_no <> ''` 的记录生效。导入时空流水号行视为失败行，不写入明细。

索引：

- 汇总查询：`org_id + accounting_period + live_promoter + receipt_merchant`
- 店铺筛选：`org_id + shop_id + accounting_period`
- 任务明细：`task_id`
- 文件明细：`file_id`

## 导入处理

### 上传入口

新增页面 `frontend/src/views/reconciliation-checklist/upload.vue`。

流程：

1. 用户下载模板或选择文件。
2. 前端使用 SheetJS 读取第一张非空 sheet 的表头。
3. 校验表头匹配。
4. 创建统一上传批次。
5. 获取 OSS STS。
6. multipart 上传到 OSS。
7. 调用上传 callback，传入 `parsed_type = "对账清单"`。
8. 后端创建对账清单文件记录和任务，并投递 Celery。

后端在现有 `UploadService.handle_file_callback` 中识别 `parsed_type == "对账清单"`，然后派生独立对账清单文件记录和任务。这样可以复用现有上传批次、OSS STS、配额校验和审计日志，同时保持解析、任务、汇总和导出逻辑独立。

### Celery 处理

新增任务建议为：

`app.tasks.reconciliation_checklist.run_reconciliation_checklist_task`

处理步骤：

1. 标记任务 `running`，文件 `running`。
2. 从 OSS 下载源文件到临时文件。
3. 用 openpyxl 读取 workbook。
4. 找到第一张非空 sheet。
5. 后端重复校验表头。
6. 逐行解析。
7. 必填校验：
   - 平台非空
   - 店铺非空
   - 动账时间可解析
   - 动账流水号非空
   - 直播推广方非空
   - 收款商家非空
8. 用 `动账时间` 得到 `accounting_year`、`accounting_month`、`accounting_period`。
9. 按 `平台 + 店铺` 获取或创建店铺。
10. 确保对应年月分区存在。
11. 用唯一键 upsert 明细。
12. 更新任务统计和结果摘要。
13. 成功时标记任务、文件为 `success`；异常时标记为 `failed`，保留错误信息。

金额解析：

- `GMV`、`直播推广佣金`、`应付商家净额` 统一用 Decimal，保留 2 位。
- 空金额按 0 处理。
- 无法解析的金额记为失败行，不写入明细。

时间解析：

- 支持 Excel datetime、Excel serial date、`YYYY-MM-DD HH:mm:ss`、`YYYY/MM/DD HH:mm:ss`。
- 无法解析的时间记为失败行。

Upsert 语义：

- 同唯一键已存在时，更新业务字段、`task_id`、`file_id`、`source_row_number`、`raw_row` 和 `updated_at`。
- 同唯一键不存在时新增。
- 每个任务统计 `inserted_rows` 和 `updated_rows`。

## API 设计

新增 router：

`backend/app/api/v1/reconciliation_checklist.py`

前缀：

`/api/v1/reconciliation-checklist`

接口：

- `GET /template`：下载空模板。
- `GET /tasks`：分页查询导入任务。
- `POST /tasks/{task_id}/retry`：重试失败任务。
- `GET /summary`：分页查询汇总。
- `GET /summary/details`：查询某条汇总的商品维度明细。
导出接入现有下载中心：

- 新增 export type：`reconciliation_checklist.summary`
- 新增 module：`reconciliation_checklist`
- 前端从汇总页调用 `submitExportJob`，生成后进入下载中心下载。

权限：

- 组织范围沿用现有 `resolve_org_ids` 规则。
- 普通用户只能看本组织数据。
- 超级管理员可以按组织筛选。
- 店铺可见性沿用现有 `active_shop_filter`。

## 汇总

汇总维度：

`org_id + accounting_period + live_promoter + receipt_merchant`

列表字段：

- 年月
- 组织
- 直播推广方
- 收款商家
- 货品数量
- 订单总金额
- 直播佣金总金额
- 应付商家净额总金额

货品数量口径：

- 汇总列表使用明细行数，字段名仍显示为“货品数量”。
- 商品维度抽屉中按 `商品名称` 聚合后展示商品数量和金额合计。

筛选：

- 年月或年月范围。
- 组织。
- 直播推广方。
- 收款商家。
- 店铺。
- 关键词，匹配直播推广方、收款商家、商品名称。

商品维度明细：

按 `商品名称` 聚合，返回：

- 商品名称
- 货品数量
- GMV 合计
- 直播推广佣金合计
- 应付商家净额合计

## 导出

导出触发：

- 汇总页支持勾选汇总行。
- 点击“导出选中”后创建下载中心任务。
- 不选中时不允许导出，避免误导出过多 sheet。

导出分 sheet：

每个选中汇总行生成一个 sheet，sheet 名按：

`YYYYMM + 收款商家 + 直播推广方`

Excel sheet 名限制 31 字符，导出时应清理非法字符并截断。如果截断后重名，追加序号。

sheet 样式参考附件：

- 第一行合并居中标题：`直播推广佣金明细`
- 第二行展示：
  - `收款商家`
  - 收款商家名称
  - `YYYY年M月`
  - `直播推广方`
  - 直播推广方名称
- 表格列：
  - 直播编号
  - 货品名称
  - 订单金额
  - 直播推广佣金
  - 应付商家净额
- 直播编号为当前 sheet 内商品明细序号，从 1 开始。
- 至少预留 10 行商品明细位置。
- 最后一行为 `总计`，金额列使用合计值。
- 数字列保留 2 位，空值显示 `-`。
- 边框、字体、列宽和合并单元格尽量贴近附件。

导出数据口径：

- sheet 内数据来自 `summary/details` 的商品维度聚合。
- 每个 sheet 的合计等于对应汇总行金额。

## 前端导航

新增独立菜单组：

`对账清单`

子页面：

- `上传`
- `任务`
- `汇总`

建议路由：

- `/reconciliation-checklist/upload`
- `/reconciliation-checklist/tasks`
- `/reconciliation-checklist/summary`

隐藏旧商家对账：

- 当前 `DefaultLayout.vue` 已通过 `merchantReconciliationMenuEnabled = false` 隐藏旧商家对账菜单。
- 本次保持该开关为 false。
- 不删除旧 `merchant-reconciliation` routes，避免直接访问历史页面或已有书签时出现不可预期影响。
- 下载中心模块筛选中可保留旧“商家对账”选项，同时新增“对账清单”模块。

## 前端页面设计

### 上传页

复用现有上传中心交互模式：

- 顶部说明区域展示模板格式和流程。
- 操作区提供“下载模板”和拖拽上传。
- 文件列表展示文件名、表头校验、状态、错误信息、上传进度。
- 提交成功后提示用户到“任务”页查看处理状态。

### 任务页

字段：

- 文件名
- 组织
- 状态
- 总行数
- 成功行数
- 失败行数
- 新增行数
- 更新行数
- 创建时间
- 完成时间
- 错误信息

操作：

- 搜索
- 刷新
- 重试失败任务

### 汇总页

字段：

- 年月
- 组织
- 直播推广方
- 收款商家
- 货品数量
- 订单总金额
- 直播佣金总金额
- 应付商家净额总金额

操作：

- 查询
- 重置
- 刷新
- 选中导出
- 查看明细

明细抽屉：

- 展示当前汇总行标识和金额指标。
- 表格按商品名称展示聚合明细。

## 测试策略

后端测试：

- 表头校验接受模板原表头。
- 表头校验兼容 `动账流水号`。
- 表头缺失时失败。
- 动账时间解析年月。
- 平台 + 店铺 自动创建店铺。
- 同唯一键重复导入执行更新，不重复插入。
- 汇总按 `年月 + 直播推广方 + 收款商家` 聚合。
- 商品维度明细按商品名称聚合。
- 导出 workbook 生成多个 sheet，sheet 名去非法字符并避免重名。
- 导出合计行等于汇总金额。

前端测试：

- 上传页表头校验通过和失败。
- API 参数构造正确。
- 汇总选中导出参数包含选中 key。
- 菜单出现“对账清单”，旧“商家对账”菜单不出现。

手工验证：

- 下载模板只含表头。
- 上传模板数据后任务成功。
- 汇总列表与样例数据金额一致。
- 查看明细按商品名称聚合。
- 下载中心导出文件打开后样式接近附件。

## 风险与处理

- 大文件导入可能较慢：使用 Celery 异步处理，并在任务页展示进度和统计。
- Excel sheet 名超长或重名：清理、截断并追加序号。
- 同一个文件跨多个月份：允许处理，明细按 `动账时间` 分区；任务结果摘要列出涉及年月。
- 前端校验可被绕过：后端 Celery 必须重复校验表头。
- 旧商家对账不能受影响：新模型、新 API、新前端目录、新 export type；旧菜单仅隐藏，不删除旧功能。
