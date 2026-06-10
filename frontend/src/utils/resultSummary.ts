export interface ResultSummaryItem {
    key: string;
    label: string;
    value: string;
}

export interface ResultSummaryOptions {
    excludeKeys?: string[];
    showPerformanceMetrics?: boolean;
}

const RESULT_SUMMARY_LABELS: Record<string, string> = {
    type: "文件类型",
    red_sheet_id: "红单文件ID",
    bank_flow_file_id: "银行流水文件ID",
    order_index_rows: "订单索引写入行数",
    summary_ids: "汇总记录ID",
    total_rows: "总行数",
    processed_rows: "处理行数",
    success_rows: "成功行数",
    failed_rows: "失败行数",
    inserted_rows: "新增行数",
    updated_rows: "更新行数",
    deleted_rows: "覆盖删除行数",
    matched_rows: "匹配明细数",
    matched_row_count: "匹配行数",
    unmatched_rows: "未匹配行数",
    purchase_rows: "采购明细行数",
    payment_rows: "货款明细行数",
    groups: "汇总分组数",
    summary_groups: "汇总分组数",
    errors: "错误明细",
    warnings: "处理提示",
    dependency_type: "依赖数据",
    parse_success_rows: "解析成功行数",
    parse_failed_rows: "解析失败行数",
    missing_order_count: "缺少订单创建时间行数",
    missing_order_samples: "缺少订单创建时间订单样例",
    fallback_time_label: "兜底时间字段",
    fallback_time_count: "兜底归属年月行数",
    fallback_time_samples: "兜底归属年月订单样例",
    raw_detail_rows: "原始明细行数",
    deduped_detail_rows: "去重后明细行数",
    rebuilt_summary_scope_count: "重建汇总行范围数",
    scope_count: "覆盖范围数",
    periods: "涉及年月",
    parse_seconds: "解析耗时秒",
    partition_seconds: "分区检查耗时秒",
    build_details_seconds: "明细构建耗时秒",
    replace_details_seconds: "明细替换耗时秒",
    rebuild_summary_seconds: "汇总重建耗时秒",
};

const VALUE_LABELS: Record<string, Record<string, string>> = {
    type: {
        red_sheet: "红单",
        bank_flow: "银行流水",
        bic: "BIC",
    },
    文件类型: {
        red_sheet: "红单",
        bank_flow: "银行流水",
        bic: "BIC",
    },
    dependency_type: {
        order_index: "订单索引",
    },
    依赖数据: {
        order_index: "订单索引",
    },
};

const SEMICOLON_LIST_KEYS = new Set([
    "errors",
    "warnings",
    "错误明细",
    "处理提示",
    "missing_order_samples",
    "fallback_time_samples",
    "缺少订单创建时间订单样例",
    "兜底归属年月订单样例",
]);

const PERFORMANCE_SUMMARY_KEYS = new Set([
    "文件下载耗时秒",
    "解析耗时秒",
    "明细入库耗时秒",
    "汇总重建耗时秒",
    "分区检查耗时秒",
    "明细构建耗时秒",
    "明细替换耗时秒",
    "parse_seconds",
    "partition_seconds",
    "build_details_seconds",
    "replace_details_seconds",
    "rebuild_summary_seconds",
]);

function summaryLabel(key: string) {
    return RESULT_SUMMARY_LABELS[key] || key;
}

function isEmptyText(value: string) {
    return value.trim() === "";
}

function primitiveToText(value: string | number | boolean) {
    if (typeof value === "boolean") return value ? "是" : "否";
    return String(value);
}

function formatPrimitiveList(key: string, values: Array<string | number | boolean>) {
    const separator = SEMICOLON_LIST_KEYS.has(key) ? "；" : "、";
    return values.map(primitiveToText).filter((item) => !isEmptyText(item)).join(separator);
}

export function formatResultSummaryValue(key: string, value: unknown): string {
    if (value == null || value === "") return "-";

    if (typeof value === "string") {
        return VALUE_LABELS[key]?.[value.toLowerCase()] || value;
    }

    if (typeof value === "number" || typeof value === "boolean") {
        return primitiveToText(value);
    }

    if (Array.isArray(value)) {
        if (value.length === 0) return "无";
        if (
            value.every(
                (item) =>
                    item == null ||
                    typeof item === "string" ||
                    typeof item === "number" ||
                    typeof item === "boolean",
            )
        ) {
            const text = formatPrimitiveList(
                key,
                value.filter(
                    (item): item is string | number | boolean => item != null,
                ),
            );
            return text || "无";
        }
        return JSON.stringify(value, null, 2);
    }

    if (typeof value === "object") {
        return JSON.stringify(value, null, 2);
    }

    return String(value);
}

export function resultSummaryItems(
    value: Record<string, unknown> | null | undefined,
    options: ResultSummaryOptions = {},
): ResultSummaryItem[] {
    if (!value) return [];
    const excluded = new Set(options.excludeKeys || []);
    const showPerformanceMetrics = options.showPerformanceMetrics ?? true;
    return Object.entries(value)
        .filter(
            ([key]) =>
                !excluded.has(key) &&
                (showPerformanceMetrics || !PERFORMANCE_SUMMARY_KEYS.has(key)),
        )
        .map(([key, itemValue]) => ({
            key,
            label: summaryLabel(key),
            value: formatResultSummaryValue(key, itemValue),
        }));
}
