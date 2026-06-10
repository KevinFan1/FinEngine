import {
    checklistFileTypeLabel,
    findChecklistHeaderRow,
    loadXlsx,
    validateChecklistHeadersForFileType,
} from "./common.ts";

export const MANUAL_EDIT_MAX_SUB_ORDERS = 100;

export const MANUAL_EDIT_STATE_KEYS = {
    invoice: "reconciliation-checklist:invoice-edits",
    merchant: "reconciliation-checklist:merchant-edits",
} as const;

export function parseManualEditSubOrders(raw: string) {
    const seen = new Set<string>();
    const items: string[] = [];

    for (const part of raw.split(/[\n,，]/)) {
        const value = part.trim();
        if (!value || seen.has(value)) continue;
        seen.add(value);
        items.push(value);
    }

    return items;
}

export function manualEditLimitMessage(count: number) {
    return `已识别 ${count} 个子订单号，单次最多查询 100 个子订单号`;
}

export const MANUAL_EDIT_AMOUNT_COLUMNS = [
    { key: "platform_subsidy", label: "平台补贴", shortLabel: "平台补", width: 92 },
    { key: "talent_subsidy", label: "达人补贴", shortLabel: "达人补", width: 92 },
    { key: "douyin_pay_subsidy", label: "抖音支付补贴", shortLabel: "支付补", width: 92 },
    { key: "douyin_monthly_pay_subsidy", label: "抖音月付营销补贴", shortLabel: "月付补", width: 92 },
    { key: "bank_subsidy", label: "银行补贴", shortLabel: "银行补", width: 92 },
    { key: "user_paid_amount", label: "用户实付（订单金额）", shortLabel: "用户实付", width: 108 },
    { key: "platform_service_fee", label: "平台服务费", shortLabel: "平台服", width: 92 },
    { key: "talent_commission", label: "达人佣金", shortLabel: "达人佣", width: 92 },
    { key: "investment_service_fee", label: "招商服务费", shortLabel: "招商服", width: 92 },
] as const;

export async function validateManualEditUploadHeaders(file: File, expectedFileType: string) {
    const XLSX = await loadXlsx();
    const workbook = XLSX.read(await file.arrayBuffer(), { type: "array", sheetRows: 5 });
    let bestMissing: string[] = [];
    let sawRows = false;

    for (const sheetName of workbook.SheetNames) {
        const sheet = workbook.Sheets[sheetName];
        const rows = XLSX.utils.sheet_to_json<unknown[]>(sheet, {
            header: 1,
            raw: false,
            defval: "",
        });
        const nonEmptyRows = rows.filter((row) => row.some((cell) => String(cell || "").trim()));
        if (!nonEmptyRows.length) continue;
        sawRows = true;
        const headerRow = findChecklistHeaderRow(nonEmptyRows);
        if (!headerRow) continue;
        const result = validateChecklistHeadersForFileType(headerRow.cells, expectedFileType);
        if (result.valid) return;
        if (!bestMissing.length || result.missing.length < bestMissing.length) {
            bestMissing = result.missing;
        }
    }

    if (!sawRows) {
        throw new Error("上传文件为空，请使用包含表头的修改模板");
    }
    if (bestMissing.length) {
        throw new Error(`上传文件不是${checklistFileTypeLabel(expectedFileType)}模板，缺少：${bestMissing.join("、")}`);
    }
    throw new Error(`未找到${checklistFileTypeLabel(expectedFileType)}模板表头`);
}
