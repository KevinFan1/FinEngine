export const CHECKLIST_FILE_TYPE_SOURCE = "对账清单-原始数据";
export const CHECKLIST_FILE_TYPE_INVOICE = "对账清单-发票更新";
export const CHECKLIST_FILE_TYPE_MERCHANT = "对账清单-商家更新";
export const CHECKLIST_FILE_TYPE = CHECKLIST_FILE_TYPE_SOURCE;
export type ChecklistTemplateType = "source" | "invoice" | "merchant";

export const SOURCE_HEADERS = [
    "进驻的直播平台",
    "结算时间",
    "子订单号",
    "下单时间",
    "商品ID",
    "商品名称",
    "商品数量",
    "达人名称",
    "平台补贴",
    "达人补贴",
    "抖音支付补贴",
    "抖音月付营销补贴",
    "银行补贴",
    "用户实付 （订单金额）",
    "平台服务费",
    "达人佣金",
    "招商服务费",
    "商户主体名称",
    "客服代码",
    "收款商家",
    "直播推广佣金",
    "佣金率",
    "应付商家净额",
    "付款金额",
    "付款时间（商家）",
    "开票时间",
    "发票号码",
];
export const SOURCE_OPTIONAL_HEADERS = ["应付商家净额余额"];
export const INVOICE_UPDATE_HEADERS = ["唯一ID", "子订单号", "收款商家", "开票时间", "发票号码"];
export const MERCHANT_UPDATE_HEADERS = ["唯一ID", "子订单号", "收款商家", "应付商家净额", "付款金额", "付款时间（商家）"];

export interface ChecklistHeaderValidation {
    valid: boolean;
    missing: string[];
    fileType: string;
}

const HEADER_SPECS = [
    { fileType: CHECKLIST_FILE_TYPE_SOURCE, headers: SOURCE_HEADERS },
    { fileType: CHECKLIST_FILE_TYPE_MERCHANT, headers: MERCHANT_UPDATE_HEADERS },
    { fileType: CHECKLIST_FILE_TYPE_INVOICE, headers: INVOICE_UPDATE_HEADERS },
];

const HEADER_ALIASES: Record<string, string> = {
    商家主体名称: "商户主体名称",
    "用户实付(订单金额)": "用户实付 （订单金额）",
    "用户实付（订单金额）": "用户实付 （订单金额）",
    用户实付订单金额: "用户实付 （订单金额）",
    系统行定位值: "唯一ID",
};

export function canonicalChecklistHeader(header: unknown) {
    const text = String(header || "")
        .trim()
        .replace("帐", "账")
        .replace(/\s+/g, "")
        .replace(/（/g, "(")
        .replace(/）/g, ")");
    return HEADER_ALIASES[text] || text;
}

export function validateChecklistHeaders(headers: unknown[]): ChecklistHeaderValidation {
    const present = new Set(headers.map(canonicalChecklistHeader).filter(Boolean));
    let best = { fileType: "", missing: [] as string[] };
    for (const spec of HEADER_SPECS) {
        const missing = spec.headers.filter((header) => !present.has(canonicalChecklistHeader(header)));
        if (missing.length === 0) {
            return { valid: true, missing: [], fileType: spec.fileType };
        }
        if (!best.fileType || missing.length < best.missing.length) {
            best = { fileType: spec.fileType, missing };
        }
    }
    return { valid: false, missing: best.missing, fileType: best.fileType };
}

export function validateChecklistHeadersForFileType(headers: unknown[], fileType: string): ChecklistHeaderValidation {
    const spec = HEADER_SPECS.find((item) => item.fileType === fileType);
    if (!spec) return { valid: false, missing: [], fileType };
    const present = new Set(headers.map(canonicalChecklistHeader).filter(Boolean));
    const missing = spec.headers.filter((header) => !present.has(canonicalChecklistHeader(header)));
    return { valid: missing.length === 0, missing, fileType };
}

export function findChecklistHeaderRow(rows: unknown[][]) {
    let best: { cells: unknown[]; result: ChecklistHeaderValidation } | null = null;
    for (const row of rows) {
        const cells = Array.isArray(row) ? row : [];
        const result = validateChecklistHeaders(cells);
        if (result.valid) return { cells, result };
        if (!best || result.missing.length < best.result.missing.length) best = { cells, result };
    }
    return null;
}

export function checklistFileTypeLabel(fileType?: string) {
    return fileType || "对账清单";
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
    if (!xlsxPromise) xlsxPromise = import("xlsx");
    return xlsxPromise;
}

export async function downloadChecklistTemplate(templateType: ChecklistTemplateType = "source") {
    const XLSX = await loadXlsx();
    const workbook = XLSX.utils.book_new();
    const templateMap: Record<ChecklistTemplateType, { sheetName: string; filename: string; headers: string[] }> = {
        source: {
            sheetName: "原始数据-表头",
            filename: "对账清单原始数据模板.xlsx",
            headers: [...SOURCE_HEADERS, ...SOURCE_OPTIONAL_HEADERS],
        },
        invoice: {
            sheetName: "发票取数-更新",
            filename: "对账清单发票更新模板.xlsx",
            headers: INVOICE_UPDATE_HEADERS,
        },
        merchant: {
            sheetName: "商家取数-更新",
            filename: "对账清单商家更新模板.xlsx",
            headers: MERCHANT_UPDATE_HEADERS,
        },
    };
    const template = templateMap[templateType];
    const worksheet = XLSX.utils.aoa_to_sheet([template.headers]);
    worksheet["!cols"] = template.headers.map((header) => ({ wch: Math.max(12, header.length * 2 + 4) }));
    XLSX.utils.book_append_sheet(workbook, worksheet, template.sheetName);
    const buffer = XLSX.write(workbook, { bookType: "xlsx", type: "array" });
    downloadFile(new Blob([buffer], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), template.filename);
}
