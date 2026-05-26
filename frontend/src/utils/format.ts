/**
 * Formatting and parsing utilities for FinEngine
 */

export interface ParsedFileName {
    year: number;
    month: number;
    type: string;
    shop: string;
}

/**
 * Parse financial file name.
 * Expected format: {YY|YYYY年MM月}_{性质}_{店铺名称}.xlsx/.xlsm/.xls/.csv
 * Examples:
 *   26年02月_动账_宝蕴天工.xlsx
 *   26年02月_gmv_快手店铺.xlsx
 *   2026年02月_动账_宝蕴天工.xlsx
 *   26年2月_bic_宝蕴天工.xlsx
 *   26年02月_运费险_宝蕴天工.xlsx
 *   26年02月_订单_快手店铺.xlsx
 *   26年02月_其他服务款_小红书店铺.xlsx
 */
export function parseFileName(filename: string): ParsedFileName | null {
    // Remove one or more trailing spreadsheet extensions, e.g. .xlsx.xlsx
    const nameWithoutExt = filename.replace(
        /(?:\.(?:xlsx|xlsm|xls|csv))+$/i,
        "",
    );

    // Match pattern: YY/YYYY年M(M)月_性质_店铺
    const regex = /^(\d{2}|\d{4})年(\d{1,2})月[ _](动账|gmv|bic|运费险|订单|其他服务款)[ _](.+)$/i;
    const match = nameWithoutExt.match(regex);

    if (!match) return null;

    const year = match[1].length === 2 ? 2000 + parseInt(match[1], 10) : parseInt(match[1], 10);
    const month = parseInt(match[2], 10);
    if (month < 1 || month > 12) return null;

    const lowerType = match[3].toLowerCase();
    const type = lowerType === "bic" || lowerType === "gmv" ? lowerType : match[3];
    const shop = match[4]
        .replace(/(?:\.(?:xlsx|xlsm|xls|csv))+$/i, "")
        .trim();
    if (!shop) return null;

    return { year, month, type, shop };
}

/**
 * Format a date string or Date object to 'YYYY-MM-DD HH:mm:ss'
 */
export function formatDateTime(date: string | Date | null | undefined): string {
    if (!date) return "-";
    const d = typeof date === "string" ? new Date(date) : date;
    if (isNaN(d.getTime())) return "-";

    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const hours = String(d.getHours()).padStart(2, "0");
    const minutes = String(d.getMinutes()).padStart(2, "0");
    const seconds = String(d.getSeconds()).padStart(2, "0");

    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

/**
 * Format a date string or Date object to 'YYYY-MM-DD'
 */
export function formatDate(date: string | Date | null | undefined): string {
    if (!date) return "-";
    const d = typeof date === "string" ? new Date(date) : date;
    if (isNaN(d.getTime())) return "-";

    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");

    return `${year}-${month}-${day}`;
}

/**
 * Format file size from bytes to human readable string
 */
export function formatFileSize(bytes: number | null | undefined): string {
    if (bytes === null || bytes === undefined || bytes < 0) return "-";
    if (bytes === 0) return "0 B";

    const units = ["B", "KB", "MB", "GB", "TB"];
    const k = 1024;
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    const size = bytes / Math.pow(k, i);

    return `${size.toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
}

/**
 * Format a number with thousand separators (千分位)
 */
export function formatNumber(num: number | null | undefined): string {
    if (num === null || num === undefined) return "-";
    return num.toLocaleString("zh-CN");
}

/**
 * Format money with thousand separators and 2 decimal places
 * Used for financial columns in tables
 */
export function formatMoney(amount: number | null | undefined): string {
    if (amount === null || amount === undefined) return "-";
    return amount.toLocaleString("zh-CN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

/**
 * Normalize a filename fragment.
 */
export function sanitizeFilenamePart(
    value: string | number | null | undefined,
): string {
    if (value === null || value === undefined) return "";
    const text = String(value).trim();
    if (!text) return "";
    return text.replace(/[\\/:*?"<>|]+/g, "_").replace(/\s+/g, " ");
}

/**
 * Build a safe export filename from ordered parts.
 */
export function buildExportFilename(
    parts: Array<string | number | null | undefined>,
    extension = "xlsx",
): string {
    const safeParts = parts
        .map((part) => sanitizeFilenamePart(part))
        .filter(Boolean);
    const safeExtension = extension.replace(/^\.+/, "") || "xlsx";
    return `${safeParts.join("_")}.${safeExtension}`;
}

/**
 * Compact a multi-select label for filenames.
 */
export function summarizeFilenameValues(
    values: Array<string | number | null | undefined>,
    emptyLabel: string,
    maxItems = 2,
): string {
    const labels = values.map((item) => sanitizeFilenamePart(item)).filter(Boolean);
    if (!labels.length) return emptyLabel;
    if (labels.length <= maxItems) return labels.join("+");
    return `${labels.slice(0, maxItems).join("+")}等${labels.length}项`;
}

/**
 * Format currency (CNY) with ¥ symbol
 */
export function formatCurrency(amount: number | null | undefined): string {
    if (amount === null || amount === undefined) return "-";
    return `¥${amount.toLocaleString("zh-CN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    })}`;
}

/**
 * Role display name mapping
 */
export const roleLabelMap: Record<string, string> = {
    superadmin: "超级管理员",
    org_admin: "组织管理员",
    member: "普通成员",
};

/**
 * Get role display label
 */
export function getRoleLabel(role: string): string {
    return roleLabelMap[role] || role;
}

/**
 * Status display mapping for various entities
 */
export const statusLabelMap: Record<string, { label: string; type: string }> = {
    active: { label: "启用", type: "success" },
    disabled: { label: "禁用", type: "danger" },
    queued: { label: "排队中", type: "info" },
    running: { label: "运行中", type: "warning" },
    success: { label: "成功", type: "success" },
    partial_success: { label: "部分成功", type: "warning" },
    failed: { label: "失败", type: "danger" },
    expired: { label: "已过期", type: "info" },
    cancelled: { label: "已取消", type: "info" },
};

/**
 * Platform display name mapping
 */
export const platformLabelMap: Record<string, string> = {
    douyin: "抖音",
    kuaishou: "快手",
    xiaohongshu: "小红书",
    weixin_video: "微信小店",
    tmall: "天猫",
    taobao: "淘宝",
    alipay: "支付宝",
    qianniu: "千牛",
    miniprogram: "小程序",
    抖音: "抖音",
    抖店: "抖音",
    快手: "快手",
    小红书: "小红书",
    视频号: "微信小店",
    微信小店: "微信小店",
    天猫: "天猫",
    淘宝: "淘宝",
    支付宝: "支付宝",
    千牛: "千牛",
    小程序: "小程序",
};

const platformClassMap: Record<string, string> = {
    douyin: "douyin",
    抖音: "douyin",
    抖店: "douyin",
    kuaishou: "kuaishou",
    快手: "kuaishou",
    xiaohongshu: "xiaohongshu",
    小红书: "xiaohongshu",
    weixin_video: "weixin-video",
    weixinvideo: "weixin-video",
    视频号: "weixin-video",
    微信小店: "weixin-video",
    tmall: "tmall",
    天猫: "tmall",
    taobao: "taobao",
    淘宝: "taobao",
    alipay: "alipay",
    支付宝: "alipay",
    qianniu: "qianniu",
    千牛: "qianniu",
    miniprogram: "miniprogram",
    mini_program: "miniprogram",
    小程序: "miniprogram",
};

/**
 * Get platform display label
 */
export function getPlatformLabel(platform: string): string {
    return platformLabelMap[platform] || platform;
}

/**
 * Get platform tag CSS class for consistent platform colors.
 */
export function getPlatformTagClass(
    platform: string | null | undefined,
): string {
    if (!platform) return "platform-tag platform-tag--default";
    const key = platform.trim();
    const className = platformClassMap[key] || platformClassMap[key.toLowerCase()] || "default";
    return `platform-tag platform-tag--${className}`;
}

/**
 * Type display name mapping for file types
 */
export const typeLabelMap: Record<string, { label: string; tagType: string }> =
    {
        动账: { label: "动账", tagType: "" },
        gmv: { label: "GMV", tagType: "primary" },
        bic: { label: "BIC", tagType: "success" },
        运费险: { label: "运费险", tagType: "warning" },
        订单: { label: "订单", tagType: "info" },
        其他服务款: { label: "其他服务款", tagType: "warning" },
    };
