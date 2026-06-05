<template>
    <div class="page-container dashboard-page">
        <section class="dashboard-hero">
            <div class="hero-copy">
                <span class="hero-kicker">数据总览</span>
                <h2>首页</h2>
                <p>
                    围绕对账清单处理结果，集中查看任务规模、GMV、商家覆盖和最近处理情况。
                </p>
            </div>
            <div class="hero-meta">
                <span>{{ userStore.displayName || "当前用户" }}</span>
                <span v-if="userStore.userInfo?.org_name">{{
                    userStore.userInfo.org_name
                }}</span>
                <span>{{ metrics.year }} 年</span>
                <!-- <el-button text type="primary" :loading="loading" @click="fetchMetrics">刷新数据</el-button> -->
            </div>
        </section>

        <section class="dashboard-metrics" :aria-busy="loading">
            <article
                v-for="card in metricCards"
                :key="card.label"
                class="metric-card"
                :class="card.className"
            >
                <div class="metric-card__head">
                    <span>{{ card.label }}</span>
                    <small>{{ card.badge }}</small>
                </div>
                <strong>{{ card.value }}</strong>
                <p>{{ card.hint }}</p>
            </article>
        </section>

        <section class="dashboard-grid">
            <article class="panel-card chart-panel chart-panel--wide">
                <div class="panel-header">
                    <div>
                        <span class="panel-kicker">Monthly Tasks</span>
                        <h3>{{ metrics.year }} 年每月处理任务数量</h3>
                    </div>
                    <span class="panel-note">按任务完成时间统计</span>
                </div>
                <div
                    ref="taskChartRef"
                    class="chart-box"
                    role="img"
                    aria-label="全年每月处理任务数量柱状图"
                ></div>
                <el-empty
                    v-if="!loading && !hasMonthlyTaskData"
                    class="chart-empty"
                    description="暂无本年度处理任务"
                />
            </article>

            <article class="panel-card chart-panel">
                <div class="panel-header">
                    <div>
                        <span class="panel-kicker">Monthly GMV</span>
                        <h3>{{ metrics.year }} 年每月 GMV</h3>
                    </div>
                    <span class="panel-note">按动账月份统计</span>
                </div>
                <div
                    ref="amountChartRef"
                    class="chart-box"
                    role="img"
                    aria-label="全年每月 GMV 面积图"
                ></div>
                <el-empty
                    v-if="!loading && !hasMonthlyAmountData"
                    class="chart-empty"
                    description="暂无本年度 GMV"
                />
            </article>

            <article class="panel-card merchant-panel">
                <div class="panel-header">
                    <div>
                        <span class="panel-kicker">Top Merchants</span>
                        <h3>商家 GMV Top 5</h3>
                    </div>
                    <span class="panel-note">按商家维度</span>
                </div>
                <div v-if="metrics.top_merchants.length" class="merchant-list">
                    <div
                        v-for="(merchant, index) in metrics.top_merchants"
                        :key="merchant.merchant_id"
                        class="merchant-row"
                    >
                        <span class="rank">{{ index + 1 }}</span>
                        <div class="merchant-info">
                            <strong>{{
                                merchant.merchant_name || "未命名商家"
                            }}</strong>
                            <div class="merchant-bar">
                                <span
                                    :style="{
                                        width: merchantBarWidth(
                                            merchant.total_order_amount,
                                        ),
                                    }"
                                ></span>
                            </div>
                        </div>
                        <b>{{
                            formatCompactCurrency(merchant.total_order_amount)
                        }}</b>
                    </div>
                </div>
                <el-empty
                    v-else
                    class="panel-empty"
                    description="暂无商家排行"
                />
            </article>

            <article class="panel-card recent-panel">
                <div class="panel-header">
                    <div>
                        <span class="panel-kicker">Recent Runs</span>
                        <h3>最近处理任务</h3>
                    </div>
                    <span class="panel-note">最多 5 条</span>
                </div>
                <div v-if="metrics.recent_tasks.length" class="recent-list">
                    <div
                        v-for="task in metrics.recent_tasks"
                        :key="task.id"
                        class="recent-row"
                    >
                        <div class="recent-main">
                            <strong>{{ task.original_name }}</strong>
                            <span>{{ formatDateTime(task.finished_at) }}</span>
                        </div>
                        <div class="recent-stats">
                            <span>{{ formatInteger(task.total_rows) }} 行</span>
                            <span
                                class="status-label"
                                :class="statusClass(task.status)"
                                >{{ statusLabel(task.status) }}</span
                            >
                        </div>
                    </div>
                </div>
                <el-empty
                    v-else
                    class="panel-empty"
                    description="暂无最近任务"
                />
            </article>
        </section>
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "Dashboard" });

import { BarChart, LineChart } from "echarts/charts";
import {
    GridComponent,
    TooltipComponent,
    type GridComponentOption,
    type TooltipComponentOption,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import type { BarSeriesOption, LineSeriesOption } from "echarts/charts";
import type { ComposeOption, ECharts } from "echarts/core";
import {
    computed,
    nextTick,
    onBeforeUnmount,
    onMounted,
    ref,
    shallowRef,
} from "vue";
import {
    getReconciliationChecklistDashboardMetrics,
    type ReconciliationChecklistDashboardMetrics,
} from "@/api/reconciliationChecklist";
import { usePageRefresh } from "@/composables/pageRefresh";
import { useUserStore } from "@/stores/user";

type DashboardChartOption = ComposeOption<
    | GridComponentOption
    | TooltipComponentOption
    | BarSeriesOption
    | LineSeriesOption
>;

echarts.use([
    BarChart,
    LineChart,
    GridComponent,
    TooltipComponent,
    CanvasRenderer,
]);

const userStore = useUserStore();
const currentYear = new Date().getFullYear();

const emptyMonthlyTaskCounts = () =>
    Array.from({ length: 12 }, (_, index) => ({
        month: index + 1,
        task_count: 0,
    }));

const emptyMonthlyAmounts = () =>
    Array.from({ length: 12 }, (_, index) => ({
        month: index + 1,
        total_order_amount: "0.00",
    }));

const metrics = shallowRef<ReconciliationChecklistDashboardMetrics>({
    processed_task_count: 0,
    total_task_count: 0,
    failed_task_count: 0,
    total_rows: 0,
    total_order_amount: "0.00",
    merchant_count: 0,
    covered_month_count: 0,
    completion_rate: "0.00",
    year: currentYear,
    monthly_task_counts: emptyMonthlyTaskCounts(),
    monthly_order_amounts: emptyMonthlyAmounts(),
    top_merchants: [],
    recent_tasks: [],
});
const loading = ref(false);
const taskChartRef = ref<HTMLElement | null>(null);
const amountChartRef = ref<HTMLElement | null>(null);
let taskChartInstance: ECharts | null = null;
let amountChartInstance: ECharts | null = null;

const metricCards = computed(() => [
    {
        label: "处理任务",
        value: formatInteger(metrics.value.processed_task_count),
        badge: `${formatPercent(metrics.value.completion_rate)} 完成率`,
        hint: `累计任务 ${formatInteger(metrics.value.total_task_count)} 个，失败 ${formatInteger(metrics.value.failed_task_count)} 个`,
        className: "metric-card--tasks",
    },
    {
        label: "累计 GMV",
        value: formatCurrency(metrics.value.total_order_amount),
        badge: "订单金额",
        hint: "来自已落库的对账清单明细订单金额",
        className: "metric-card--gmv",
    },
    {
        label: "对账商家",
        value: formatInteger(metrics.value.merchant_count),
        badge: "商家口径",
        hint: "按商家维度统计，不含收款商家口径",
        className: "metric-card--merchant",
    },
    {
        label: "处理行数",
        value: formatInteger(metrics.value.total_rows),
        badge: `${formatInteger(metrics.value.covered_month_count)} 个期间`,
        hint: "已成功或部分成功任务累计解析行数",
        className: "metric-card--rows",
    },
]);

const monthlyTaskCounts = computed(() =>
    Array.from({ length: 12 }, (_, index) => {
        const month = index + 1;
        return (
            metrics.value.monthly_task_counts.find(
                (item) => item.month === month,
            )?.task_count ?? 0
        );
    }),
);

const monthlyAmounts = computed(() =>
    Array.from({ length: 12 }, (_, index) => {
        const month = index + 1;
        return Number(
            metrics.value.monthly_order_amounts.find(
                (item) => item.month === month,
            )?.total_order_amount ?? 0,
        );
    }),
);

const topMerchantMaxAmount = computed(() =>
    Math.max(
        0,
        ...metrics.value.top_merchants.map((merchant) =>
            Number(merchant.total_order_amount || 0),
        ),
    ),
);

const hasMonthlyTaskData = computed(() =>
    monthlyTaskCounts.value.some((count) => count > 0),
);
const hasMonthlyAmountData = computed(() =>
    monthlyAmounts.value.some((amount) => amount > 0),
);

function formatInteger(value: number) {
    return Number(value || 0).toLocaleString("zh-CN");
}

function formatPercent(value: string) {
    const rate = Number(value || 0);
    if (!Number.isFinite(rate)) return "0%";
    return `${rate.toFixed(2).replace(/\.00$/, "")}%`;
}

function formatCurrency(value: string) {
    const amount = Number(value || 0);
    if (!Number.isFinite(amount)) return "¥0.00";
    return amount.toLocaleString("zh-CN", {
        style: "currency",
        currency: "CNY",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

function formatCompactCurrency(value: string) {
    const amount = Number(value || 0);
    if (!Number.isFinite(amount)) return "¥0";
    if (Math.abs(amount) >= 10000)
        return `¥${(amount / 10000).toFixed(1).replace(/\.0$/, "")}万`;
    return `¥${Math.round(amount).toLocaleString("zh-CN")}`;
}

function formatDateTime(value?: string | null) {
    if (!value) return "未记录完成时间";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function statusLabel(status: string) {
    const labels: Record<string, string> = {
        success: "成功",
        partial_success: "部分成功",
        failed: "失败",
        expired: "已过期",
    };
    return labels[status] || status;
}

function statusClass(status: string) {
    if (status === "success") return "status-label--success";
    if (status === "partial_success") return "status-label--warning";
    return "status-label--neutral";
}

function merchantBarWidth(value: string) {
    const amount = Number(value || 0);
    if (!topMerchantMaxAmount.value || !Number.isFinite(amount)) return "0%";
    return `${Math.max(8, Math.round((amount / topMerchantMaxAmount.value) * 100))}%`;
}

async function fetchMetrics() {
    loading.value = true;
    try {
        metrics.value = await getReconciliationChecklistDashboardMetrics();
        await nextTick();
        renderCharts();
    } catch {
        renderCharts();
    } finally {
        loading.value = false;
    }
}

function renderCharts() {
    renderTaskChart();
    renderAmountChart();
}

function renderTaskChart() {
    if (!taskChartRef.value) return;
    if (!taskChartInstance) {
        taskChartInstance = echarts.init(taskChartRef.value);
    }
    const option: DashboardChartOption = {
        color: ["#2563EB"],
        tooltip: {
            trigger: "axis",
            axisPointer: { type: "shadow" },
            formatter(params) {
                const item = Array.isArray(params) ? params[0] : params;
                return `${item.name}<br/>处理任务：${formatInteger(Number(item.value || 0))} 个`;
            },
        },
        grid: { left: 18, right: 14, top: 20, bottom: 26, containLabel: true },
        xAxis: chartXAxis(),
        yAxis: chartYAxis({ minInterval: 1 }),
        series: [
            {
                name: "处理任务",
                type: "bar",
                data: monthlyTaskCounts.value,
                barMaxWidth: 32,
                itemStyle: { borderRadius: [8, 8, 3, 3] },
            },
        ],
    };
    taskChartInstance.setOption(option);
}

function renderAmountChart() {
    if (!amountChartRef.value) return;
    if (!amountChartInstance) {
        amountChartInstance = echarts.init(amountChartRef.value);
    }
    const option: DashboardChartOption = {
        color: ["#2563EB"],
        tooltip: {
            trigger: "axis",
            formatter(params) {
                const item = Array.isArray(params) ? params[0] : params;
                return `${item.name}<br/>GMV：${formatCurrency(String(item.value || 0))}`;
            },
        },
        grid: { left: 18, right: 14, top: 20, bottom: 26, containLabel: true },
        xAxis: chartXAxis(),
        yAxis: chartYAxis({
            formatter: (value: number) =>
                value >= 10000 ? `${Math.round(value / 10000)}万` : `${value}`,
        }),
        series: [
            {
                name: "GMV",
                type: "line",
                smooth: true,
                data: monthlyAmounts.value,
                showSymbol: false,
                lineStyle: { width: 3 },
                areaStyle: {
                    color: "rgba(96, 165, 250, 0.18)",
                },
            },
        ],
    };
    amountChartInstance.setOption(option);
}

function chartXAxis() {
    return {
        type: "category" as const,
        data: Array.from({ length: 12 }, (_, index) => `${index + 1}月`),
        axisTick: { show: false },
        axisLine: { lineStyle: { color: "#E2E8F0" } },
        axisLabel: { color: "#64748B" },
    };
}

function chartYAxis(
    options: {
        minInterval?: number;
        formatter?: (value: number) => string;
    } = {},
) {
    return {
        type: "value" as const,
        minInterval: options.minInterval,
        splitLine: { lineStyle: { color: "#E2E8F0" } },
        axisLabel: {
            color: "#64748B",
            formatter: options.formatter,
        },
    };
}

function resizeCharts() {
    taskChartInstance?.resize();
    amountChartInstance?.resize();
}

onMounted(() => {
    fetchMetrics();
    window.addEventListener("resize", resizeCharts);
});

onBeforeUnmount(() => {
    window.removeEventListener("resize", resizeCharts);
    taskChartInstance?.dispose();
    amountChartInstance?.dispose();
    taskChartInstance = null;
    amountChartInstance = null;
});

usePageRefresh(fetchMetrics);
</script>

<style scoped lang="scss">
.dashboard-page {
    --dashboard-primary: #2563eb;
    --dashboard-bg: #f8fafc;
    --dashboard-surface: #ffffff;
    --dashboard-border: #e2e8f0;
    --dashboard-success: #10b981;
    --dashboard-warning: #f59e0b;
    --dashboard-text: #1e293b;
    --dashboard-muted: #64748b;
    display: block;
    height: auto;
    min-height: 100%;
    max-width: none;
    background: var(--dashboard-bg);
}

.dashboard-hero {
    position: relative;
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 20px;
    margin-bottom: 14px;
    padding: 18px 20px;
    border: 1px solid var(--dashboard-border);
    border-radius: 18px;
    background: var(--dashboard-surface);
    box-shadow: none;
    overflow: hidden;
}

.hero-copy {
    position: relative;
    z-index: 1;
    min-width: 0;

    h2 {
        margin: 3px 0 6px;
        color: var(--dashboard-text);
        font-size: 28px;
        font-weight: 850;
        letter-spacing: -0.03em;
        line-height: 1.12;
    }

    p {
        margin: 0;
        color: var(--dashboard-muted);
        font-size: 13px;
        line-height: 1.7;
    }
}

.hero-kicker,
.panel-kicker {
    color: var(--dashboard-primary);
    font-size: 11px;
    font-weight: 850;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

.hero-meta {
    position: relative;
    z-index: 1;
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
    color: var(--dashboard-muted);
    font-size: 12px;

    span {
        padding: 6px 10px;
        border: 1px solid var(--dashboard-border);
        border-radius: 999px;
        background: var(--dashboard-surface);
    }
}

.dashboard-metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 14px;
}

.metric-card,
.panel-card {
    border: 1px solid var(--dashboard-border);
    background: var(--dashboard-surface);
    box-shadow: none;
}

.metric-card {
    position: relative;
    min-height: 132px;
    padding: 16px;
    border-radius: 18px;
    overflow: hidden;

    strong {
        display: block;
        margin: 14px 0 10px;
        color: var(--dashboard-text);
        font-size: clamp(25px, 2.6vw, 34px);
        font-weight: 850;
        letter-spacing: -0.04em;
        line-height: 1;
        font-variant-numeric: tabular-nums;
    }

    p {
        margin: 0;
        color: var(--dashboard-muted);
        font-size: 12px;
        line-height: 1.55;
    }
}

.metric-card__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    color: var(--dashboard-muted);
    font-size: 12px;
    font-weight: 750;

    small {
        flex-shrink: 0;
        padding: 3px 7px;
        border: 1px solid var(--dashboard-border);
        border-radius: 999px;
        background: var(--dashboard-bg);
        color: var(--dashboard-muted);
        font-size: 11px;
    }
}

.dashboard-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.3fr) minmax(340px, 0.7fr);
    gap: 14px;
}

.panel-card {
    position: relative;
    min-height: 320px;
    padding: 18px;
    border-radius: 20px;
    overflow: hidden;
}

.chart-panel--wide {
    grid-column: span 1;
}

.panel-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 12px;

    h3 {
        margin: 4px 0 0;
        color: var(--dashboard-text);
        font-size: 17px;
        font-weight: 820;
    }
}

.panel-note {
    flex-shrink: 0;
    color: var(--dashboard-muted);
    font-size: 12px;
}

.chart-box {
    width: 100%;
    height: 252px;
}

.chart-empty {
    position: absolute;
    inset: 74px 18px 18px;
    pointer-events: none;
}

.merchant-list,
.recent-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.merchant-row {
    display: grid;
    grid-template-columns: 28px minmax(0, 1fr) auto;
    align-items: center;
    gap: 10px;
    padding: 10px;
    border: 1px solid rgba(219, 229, 238, 0.8);
    border-radius: 14px;
    background: var(--dashboard-bg);

    b {
        color: var(--dashboard-text);
        font-size: 13px;
        font-variant-numeric: tabular-nums;
    }
}

.rank {
    display: inline-grid;
    width: 26px;
    height: 26px;
    place-items: center;
    border-radius: 9px;
    border: 1px solid var(--dashboard-border);
    background: var(--dashboard-surface);
    color: var(--dashboard-primary);
    font-size: 12px;
    font-weight: 800;
}

.merchant-info {
    min-width: 0;

    strong {
        display: block;
        overflow: hidden;
        color: var(--dashboard-text);
        font-size: 13px;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
}

.merchant-bar {
    height: 6px;
    margin-top: 8px;
    border-radius: 999px;
    background: var(--dashboard-border);
    overflow: hidden;

    span {
        display: block;
        height: 100%;
        border-radius: inherit;
        background: var(--dashboard-primary);
    }
}

.recent-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 12px;
    padding: 11px 0;
    border-bottom: 1px solid rgba(219, 229, 238, 0.86);

    &:last-child {
        border-bottom: 0;
    }
}

.recent-main {
    min-width: 0;

    strong,
    span {
        display: block;
    }

    strong {
        overflow: hidden;
        color: var(--dashboard-text);
        font-size: 13px;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    span {
        margin-top: 4px;
        color: var(--dashboard-muted);
        font-size: 12px;
    }
}

.recent-stats {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 5px;
    color: var(--dashboard-muted);
    font-size: 12px;
    font-variant-numeric: tabular-nums;
}

.status-label {
    font-weight: 750;
}

.status-label--success {
    color: var(--dashboard-success);
}

.status-label--warning {
    color: var(--dashboard-warning);
}

.status-label--neutral {
    color: var(--dashboard-muted);
}

.panel-empty {
    margin-top: 24px;
}

@media (max-width: 1280px) {
    .dashboard-metrics {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .dashboard-grid {
        grid-template-columns: 1fr;
    }
}

@container (max-width: 1120px) {
    .dashboard-hero {
        align-items: flex-start;
        flex-direction: column;
        overflow: visible;
    }

    .hero-meta {
        justify-content: flex-start;
        width: 100%;
    }
}

@media (max-width: 1120px) {
    .dashboard-hero {
        align-items: flex-start;
        flex-direction: column;
        overflow: visible;
    }

    .hero-meta {
        justify-content: flex-start;
        width: 100%;
    }
}

@media (max-width: 760px) {
    .dashboard-hero {
        align-items: flex-start;
        flex-direction: column;
        overflow: visible;
    }

    .hero-meta {
        justify-content: flex-start;
        width: 100%;
    }

    .dashboard-metrics {
        grid-template-columns: 1fr;
    }

    .panel-header,
    .recent-row {
        align-items: stretch;
        grid-template-columns: 1fr;
    }

    .recent-stats {
        align-items: flex-start;
    }
}
</style>
