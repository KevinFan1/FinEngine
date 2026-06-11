# FinEngine

FinEngine 是一个面向多平台电商财务数据的上传、解析、异步处理和汇总报表系统。当前项目重点解决财务团队从平台后台导出 Excel / CSV 后，按店铺、平台、数据年月和文件性质统一入库、统计、重算和导出的问题。

## 当前定位

系统以“文件上传 -> 后台任务 -> 动账明细 -> 汇总报表”为主流程：

1. 上传平台导出的财务文件，文件名解析出年月、性质和店铺。
2. 后端任务按平台和文件性质调用处理器，生成汇总数据或订单时间索引。
3. 任务列表展示处理状态、错误原因、结果摘要，并支持失败重试和重新统计。
4. 动账明细保留按业务年月聚合的原始统计结果。
5. 汇总报表按上传文件年月聚合，并支持人工调整金额、备注和操作日志。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 后端 API | FastAPI, Pydantic |
| 数据库 | PostgreSQL, SQLAlchemy Async, Alembic |
| 异步任务 | Celery, Redis |
| 文件处理 | openpyxl, CSV reader |
| 对象存储 | 阿里云 OSS / STS |
| 前端 | Vue 3, Vite, TypeScript, Element Plus, Pinia |
| 包管理 | uv, npm |

## 已实现功能

- 用户、组织、店铺、平台、文件规格、分类字典等基础管理。
- OSS 上传中心，支持 Excel / CSV 文件。
- 文件名解析格式：`性质_店铺明细`，例如 `gmv_快手专营店明细.xlsx`；核算年月从平台和性质对应的时间列读取。
- 文件性质支持：`动账`、`gmv`、`bic`、`运费险`、`订单`。
- 任务列表支持按年月、平台、店铺、性质、状态、关键字筛选。
- 任务失败原因和 `result_summary.errors` 前端可见，长错误支持截断和悬浮查看。
- 抖音、快手平台处理器已接入。
- 快手订单文件会写入订单时间索引。
- 快手动账、运费险按订单创建时间归属月份；缺订单时记录错误摘要，缺失部分按 0 统计。
- 订单上传成功后会自动重新排队同年月、同平台、同店铺的动账/运费险任务。
- 动账、运费险支持在任务列表手动“重新统计”。
- 汇总报表支持对 `实收GMV`、`退货费用及其他费用` 做人工调整。
- 调整金额独立存储，不污染原始动账明细；支持编辑历史调整、软删除、备注和操作日志。
- 所有业务表使用 `fin_` 前缀，模型和迁移表字段带中文注释。
- 删除操作按软删除处理。

## 平台与文件类型

### 已接入处理器

| 平台代码 | 平台名称 | 已实现类型 | 说明 |
| --- | --- | --- | --- |
| `douyin` | 抖音 | `动账`, `bic`, `运费险` | 抖音动账按现有口径计算 GMV、平台收入、费用和佣金等指标 |
| `kuaishou` | 快手 | `gmv`, `动账`, `运费险`, `订单` | 快手动账和运费险依赖订单时间索引归属月份 |

### 已配置平台

| 平台代码 | 平台名称 |
| --- | --- |
| `douyin` | 抖音 |
| `kuaishou` | 快手 |
| `xiaohongshu` | 小红书 |
| `weixin_video` | 微信小店 |
| `tmall` | 天猫 |
| `taobao` | 淘宝 |
| `miniprogram` | 小程序 |

> 已配置平台可用于基础数据维护和后续接入。真正处理文件需要在后端 `app/tasks/processors/` 中增加对应平台处理器。

## 核心数据表

| 表 | 作用 |
| --- | --- |
| `fin_organizations` | 组织 |
| `fin_users` | 用户 |
| `fin_shops` | 店铺，上传和汇总优先关联店铺 ID |
| `fin_platforms` | 平台配置 |
| `fin_file_specs` | 平台文件表头规格 |
| `fin_category_dicts` | 分类字典，用于动账备注分类 |
| `fin_upload_batches` / `fin_upload_files` | 上传批次和上传文件 |
| `fin_processing_tasks` | 后台处理任务 |
| `fin_order_indexes` | 订单号到订单创建时间的索引 |
| `fin_financial_summaries` | 原始财务汇总结果 |
| `fin_summary_adjustments` | 汇总报表人工调整记录 |
| `fin_operation_logs` | 操作日志 |

## 报表口径

### 动账明细

动账明细来自 `fin_financial_summaries`，保留原始处理结果，按业务年月、核算年月、平台和店铺记录。该页面用于查看处理器产出的基础数据，不叠加人工调整。

### 汇总报表

汇总报表按数据表核算年月聚合展示。展示和导出时会叠加 `fin_summary_adjustments`：

- `原始GMV + GMV调整 = 调整后GMV`
- `原始退货费用及其他费用 + 退货费用调整 = 调整后退货费用及其他费用`

调整记录不会回写原始汇总行，也不会改变上传文件和动账明细。

## 后端运行

进入后端目录：

```bash
cd backend
```

安装依赖：

```bash
uv sync
```

配置环境变量：

```bash
cp .env.example .env
```

至少需要配置：

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/finengine
# 缓存/验证码/防重放
REDIS_URL=redis://localhost:6379/0
# Celery 队列和结果，建议与缓存使用不同 Redis DB
CELERY_REDIS_URL=redis://localhost:6379/1
SECRET_KEY=change-this
ALIYUN_OSS_BUCKET=
ALIYUN_ACCESS_KEY_ID=
ALIYUN_ACCESS_KEY_SECRET=
```

执行迁移和初始化：

```bash
uv run migrate-upgrade
uv run seed-all
```

启动 API：

```bash
uv run dev
```

启动 Celery worker：

```bash
uv run worker
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

## 前端运行

进入前端目录：

```bash
cd frontend
```

安装依赖并启动：

```bash
npm install
npm run dev
```

构建：

```bash
npm run build
```

## 默认账号

| 角色 | 用户名 | 密码 |
| --- | --- | --- |
| 超级管理员 | `superadmin` | `admin123` |
| 组织管理员 | `admin` | `admin123` |

生产环境必须修改默认密码和 `SECRET_KEY`。

## 前端页面

| 页面 | 说明 |
| --- | --- |
| 首页 | 系统入口和关键操作引导 |
| 组织管理 | 超级管理员维护组织 |
| 用户管理 | 超级管理员、组织管理员维护用户 |
| 店铺管理 | 维护平台店铺，上传和汇总按店铺关联 |
| 上传中心 | 上传平台导出的 Excel / CSV |
| 任务列表 | 查看处理状态、错误、重试、重新统计 |
| 动账明细 | 查看原始汇总结果 |
| 汇总报表 | 按核算年月聚合、调整金额、导出 |
| 操作日志 | 查看关键操作记录 |

## 后端模块

```text
backend/app/
├── api/v1/              # FastAPI 路由
├── core/                # 配置、数据库、安全依赖
├── middleware/          # 审计中间件
├── models/              # SQLAlchemy 模型
├── schemas/             # Pydantic Schema
├── services/            # 业务服务
├── tasks/               # Celery 应用、聚合、平台处理器
└── utils/               # 金额、文本分类等工具
```

## OSS 目录约定

上传和导出文件统一按当前年月归档，方便后续整批清理：

```text
upload/{type}/{YYYYMM}/{token}_{filename}
export/{type}/{YYYYMM}/{job_id}_{token}.xlsx
```

说明：

- `YYYYMM` 使用上传或导出当天的当前年月，例如 `202606`。
- 不再从文件名或业务数据里识别年月。
- `type` 使用英文目录名，例如 `dongzhang`、`bic`、`red-sheet`、`bank-flow`、`reconciliation-checklist-source`。
- 对账清单手工修改文件分别进入 `reconciliation-checklist-invoice-edit` 和 `reconciliation-checklist-merchant-edit` 目录。

## CLI 命令速查

后端启动与检查：

```bash
cd backend
uv sync
uv run dev
uv run worker
uv run recover-queued-tasks
uv run debug-worker /path/to/file.xlsx
uv run ruff check app scripts
uv run pytest
```

数据库迁移：

```bash
cd backend
uv run migrate-current
uv run migrate-history
uv run migrate-check
uv run migrate-upgrade
uv run migrate-downgrade -1
uv run migrate-generate -m "message"
```

初始化与基础数据：

```bash
cd backend
uv run seed-all
uv run seed-platforms
uv run seed-users
uv run seed-file-specs
uv run seed-category-dicts
uv run seed-transaction-accounting-defaults
uv run seed-transaction-accounting-rules
uv run seed-transaction-major-subjects
```

分区维护：

```bash
cd backend
uv run ensure-source-partitions
uv run ensure-reconciliation-checklist-partitions
uv run repair-reconciliation-checklist-partitions --start 202601 --end 202612
```

前端：

```bash
cd frontend
npm install
npm run dev
npm run build
npm run preview
```

## 源数据清理

项目提供了手工清理源数据明细的脚本：

```bash
cd backend
uv run python scripts/clear_source_detail_rows.py --help
```

说明：

- 该脚本只清理 `fin_douyin_dongzhang_details` 和 `fin_bic_source_rows` 两张源数据表。
- 不会删除任务表、上传文件表、汇总表，也不会影响其他业务表。
- 推荐先执行 `--dry-run` 演练，确认待清理行数后再正式执行。
- `dongzhang` 按 `source_period` 清理，`bic` 按 `accounting_period` 清理。

常用命令：

```bash
# 先演练全量清理，查看两张源数据表会清掉多少行
cd backend
uv run python scripts/clear_source_detail_rows.py --all --dry-run

# 全量清空动账明细和 BIC 源数据
uv run python scripts/clear_source_detail_rows.py --all

# 只清空动账明细源数据
uv run python scripts/clear_source_detail_rows.py --target dongzhang --all

# 只清空 BIC 源数据
uv run python scripts/clear_source_detail_rows.py --target bic --all

# 先演练清理指定年月，例如 202604
uv run python scripts/clear_source_detail_rows.py --period 202604 --dry-run

# 清理指定年月，例如 202604
uv run python scripts/clear_source_detail_rows.py --period 202604

# 只清理动账明细的指定年月
uv run python scripts/clear_source_detail_rows.py --target dongzhang --period 202604

# 只清理 BIC 源数据的指定年月
uv run python scripts/clear_source_detail_rows.py --target bic --period 202604

# 先演练清理年月范围，例如 202604 到 202606
uv run python scripts/clear_source_detail_rows.py --period-start 202604 --period-end 202606 --dry-run

# 清理年月范围，例如 202604 到 202606
uv run python scripts/clear_source_detail_rows.py --period-start 202604 --period-end 202606

# 按保留期清理创建时间早于 30 天前的源数据，适合后续接 Celery 定时任务
uv run python scripts/clear_source_detail_rows.py --before-days 30 --dry-run
uv run python scripts/clear_source_detail_rows.py --before-days 30
```

## 接入新平台

1. 在 `backend/scripts/seed_platforms.py` 增加平台基础数据。
2. 在 `backend/scripts/seed_file_specs.py` 增加该平台各文件性质的表头规格。
3. 在 `backend/app/tasks/processors/` 新增平台处理器。
4. 在 `backend/app/tasks/processors/__init__.py` 注册 `platform_code -> processor`。
5. 在前端平台下拉和 `frontend/src/utils/format.ts` 增加平台展示名和标签样式。
6. 增加针对处理器的单元测试样例。

## 设计约定

- 金额计算使用 `Decimal`，避免浮点误差。
- 平台处理逻辑按处理器隔离，后续平台不要写进已有平台文件。
- 汇总调整只作用于汇总报表展示和导出，不修改原始明细。
- 订单时间索引用于解决退款、运费险等文件本身缺少订单创建时间的问题。
- 所有删除都走软删除，不做物理删除。
- 数据库表和字段需要保留中文注释。
