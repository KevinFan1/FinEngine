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

## 常用开发命令

后端：

```bash
cd backend
uv run ruff check app scripts
uv run pytest
uv run alembic current
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "message"
```

前端：

```bash
cd frontend
npm run build
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
