export const CHECKLIST_FILE_TYPE = "对账清单";
export const CHECKLIST_HEADERS = ["平台", "店铺", "动账时间", "动账流水号", "商品名称", "直播推广方", "商家", "收款商家", "订单金额", "直播推广佣金", "应付商家净额"];

const HEADER_ALIASES: Record<string, string> = {
    动帐流水号: "动账流水号",
    GMV: "订单金额",
    gmv: "订单金额",
};

export function canonicalChecklistHeader(header: unknown) {
    const text = String(header || "").trim().replace("帐", "账");
    return HEADER_ALIASES[text] || text;
}

export function validateChecklistHeaders(headers: unknown[]) {
    const present = new Set(headers.map(canonicalChecklistHeader).filter(Boolean));
    const missing = CHECKLIST_HEADERS.filter((header) => !present.has(header));
    return { valid: missing.length === 0, missing };
}

export function findChecklistHeaderRow(rows: unknown[][]) {
    for (const row of rows) {
        const cells = Array.isArray(row) ? row : [];
        const result = validateChecklistHeaders(cells);
        if (result.valid) return cells;
    }
    return null;
}

export function formatChecklistMonth(year?: number | null, month?: number | null) {
    if (!year || !month) return "-";
    return `${year}-${String(month).padStart(2, "0")}`;
}

export function formatAmount(value: string | number | null | undefined) {
    const numberValue = Number(value || 0);
    return numberValue.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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

let xlsxPromise: Promise<typeof import("xlsx")> | null = null;

export function loadXlsx() {
    if (!xlsxPromise) {
        xlsxPromise = import("xlsx");
    }
    return xlsxPromise;
}

export async function downloadChecklistTemplate() {
    const XLSX = await loadXlsx();
    const worksheet = XLSX.utils.aoa_to_sheet([CHECKLIST_HEADERS]);
    worksheet["!cols"] = CHECKLIST_HEADERS.map((header) => ({ wch: Math.max(12, header.length * 2 + 4) }));
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "对账清单");
    const buffer = XLSX.write(workbook, { bookType: "xlsx", type: "array" });
    downloadFile(new Blob([buffer], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), "对账清单模版.xlsx");
}
