export const transactionStatusOptions = [
    { label: "排队中", value: "queued" },
    { label: "处理中", value: "processing" },
    { label: "成功", value: "success" },
    { label: "部分成功", value: "partial_success" },
    { label: "失败", value: "failed" },
    { label: "已过期", value: "expired" },
];

export function taskStatusLabel(status: string) {
    return transactionStatusOptions.find((item) => item.value === status)?.label || status;
}

export function taskStatusType(status: string) {
    return ({ success: "success", partial_success: "warning", failed: "danger", expired: "info", processing: "primary", queued: "info" } as Record<string, string>)[status] || "info";
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

export function splitMonthRange(range: string[] | null | undefined) {
    const [start, end] = range || [];
    const [startYear, startMonth] = start ? start.split("-").map(Number) : [undefined, undefined];
    const [endYear, endMonth] = end ? end.split("-").map(Number) : [undefined, undefined];
    return {
        accounting_start_year: startYear,
        accounting_start_month: startMonth,
        accounting_end_year: endYear,
        accounting_end_month: endMonth,
    };
}

export function splitSingleAccountingMonth(month: string | null | undefined) {
    const [yearText, monthText] = String(month || "").split("-");
    const year = Number(yearText) || undefined;
    const monthNumber = Number(monthText) || undefined;
    if (!year || !monthNumber) {
        return {};
    }
    return {
        accounting_year: year,
        accounting_month: monthNumber,
    };
}

export function monthRangeLabel(range: string[] | null | undefined) {
    if (!range?.length) return "";
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
