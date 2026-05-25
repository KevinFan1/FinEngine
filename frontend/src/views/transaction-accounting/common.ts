import type { TransactionDetail, TransactionSummary, TransactionTask } from "@/api/transactionAccounting";

export const transactionStatusOptions = [
    { label: "排队中", value: "queued" },
    { label: "处理中", value: "processing" },
    { label: "成功", value: "success" },
    { label: "部分成功", value: "partial_success" },
    { label: "失败", value: "failed" },
];

export const detailStatusOptions = [
    { label: "已匹配", value: "matched" },
    { label: "未匹配", value: "unmatched" },
    { label: "失败", value: "failed" },
];

export const directionOptions = [
    { label: "入账", value: "入账" },
    { label: "出账", value: "出账" },
    { label: "取负", value: "取负" },
];

export const matchTypeOptions = [
    { label: "不限制", value: "none" },
    { label: "精准", value: "exact" },
    { label: "包含", value: "contains" },
    { label: "不包含", value: "not_contains" },
];

export const resultDirectionOptions = [
    { label: "原值", value: "original" },
    { label: "取正", value: "positive" },
    { label: "取负", value: "negative" },
    { label: "入账正出账负", value: "directional" },
];

export function taskStatusLabel(status: string) {
    return transactionStatusOptions.find((item) => item.value === status)?.label || status;
}

export function taskStatusType(status: string) {
    return ({ success: "success", partial_success: "warning", failed: "danger", processing: "primary", queued: "info" } as Record<string, string>)[status] || "info";
}

export function detailStatusLabel(status: string) {
    return detailStatusOptions.find((item) => item.value === status)?.label || status;
}

export function detailStatusType(status: string) {
    return ({ matched: "success", unmatched: "warning", failed: "danger" } as Record<string, string>)[status] || "info";
}

export function formatMonth(year?: number | null, month?: number | null) {
    if (!year || !month) return "-";
    return `${year}-${String(month).padStart(2, "0")}`;
}

export function formatAmount(value: string | number | null | undefined) {
    const amount = Number(value || 0);
    return amount.toLocaleString("zh-CN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

export function formatBytes(size: number) {
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

export function parseTransactionFilename(filename: string) {
    const match = filename.match(/^(\d{2}|\d{4})年(\d{1,2})月[ _](动账)[ _](.+)\.(xlsx|xlsm|xls|csv)$/i);
    if (!match) return null;
    const year = Number(match[1].length === 2 ? `20${match[1]}` : match[1]);
    const month = Number(match[2]);
    const shop = match[4].trim();
    if (!shop || month < 1 || month > 12) return null;
    return { year, month, shop };
}

export function splitMonthRange(range: string[]) {
    const [start, end] = range;
    const [startYear, startMonth] = start ? start.split("-").map(Number) : [undefined, undefined];
    const [endYear, endMonth] = end ? end.split("-").map(Number) : [undefined, undefined];
    return {
        accounting_start_year: startYear,
        accounting_start_month: startMonth,
        accounting_end_year: endYear,
        accounting_end_month: endMonth,
    };
}

export function splitUploadMonthRange(range: string[]) {
    const filters = splitMonthRange(range);
    return {
        upload_accounting_start_year: filters.accounting_start_year,
        upload_accounting_start_month: filters.accounting_start_month,
        upload_accounting_end_year: filters.accounting_end_year,
        upload_accounting_end_month: filters.accounting_end_month,
    };
}

export function monthRangeLabel(range: string[]) {
    if (!range.length) return "";
    if (range.length === 1 || range[0] === range[1]) return range[0];
    return `${range[0]} 至 ${range[1]}`;
}

export function downloadBlob(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
}

export function detailSummaryMethod({ columns, data }: { columns: any[]; data: TransactionDetail[] }) {
    return columns.map((column, index) => {
        if (index === 1) return "合计";
        if (column.property === "total_amount" || column.property === "calculated_amount") {
            return formatAmount(data.reduce((sum, item) => sum + Number(item.total_amount ?? item.calculated_amount ?? 0), 0));
        }
        return "";
    });
}

export function summaryMethod({ columns, data }: { columns: any[]; data: TransactionSummary[] }) {
    return columns.map((column, index) => {
        if (index === 1) return "合计";
        if (column.property === "row_count") {
            return data.reduce((sum, item) => sum + Number(item.row_count || 0), 0);
        }
        if (column.property === "total_amount") {
            return formatAmount(data.reduce((sum, item) => sum + Number(item.total_amount || 0), 0));
        }
        return "";
    });
}

export function taskResultText(row: TransactionTask) {
    return `${row.total_rows} 行 · 匹配 ${row.matched_rows} · 未匹配 ${row.unmatched_rows} · 失败 ${row.failed_rows}`;
}
