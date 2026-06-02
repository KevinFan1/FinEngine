import type { Shop } from "@/api/shop";

export function defaultMonth() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export function selectedMonthParts(month: string | null | undefined) {
    const [year, monthValue] = String(month || "").split("-").map(Number);
    return { accounting_year: year, accounting_month: monthValue };
}

export function formatMonth(year?: number | null, month?: number | null) {
    if (!year || !month) return "-";
    return `${year}-${String(month).padStart(2, "0")}`;
}

export function formatAccountingPeriod(period?: number | null) {
    if (!period) return "-";
    const value = String(period);
    return `${value.slice(0, 4)}-${value.slice(4, 6)}`;
}

export function formatAmount(value: string | number | null | undefined) {
    return Number(value || 0).toLocaleString("zh-CN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

export function formatPercent(value: string | number | null | undefined) {
    const rawValue = String(value ?? "").trim();
    if (!rawValue) return "-";
    const hasPercentSign = rawValue.includes("%");
    const numericValue = Number(rawValue.replace(/%/g, "").replace(/,/g, ""));
    if (!Number.isFinite(numericValue)) return rawValue;
    const percentValue = hasPercentSign || Math.abs(numericValue) > 1 ? numericValue : numericValue * 100;
    return `${percentValue.toLocaleString("zh-CN", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    })}%`;
}

export function formatBytes(size: number | null | undefined) {
    const value = Number(size || 0);
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
    return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

export function isDouyinShop(shop: Shop) {
    const platform = String(shop.platform_name || "").trim().toLowerCase();
    return ["抖音", "douyin", "抖店"].includes(platform);
}

export function downloadFile(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

let xlsxModulePromise: Promise<typeof import("xlsx")> | null = null;

export function loadXlsx() {
    if (!xlsxModulePromise) {
        xlsxModulePromise = import("xlsx");
    }
    return xlsxModulePromise;
}
