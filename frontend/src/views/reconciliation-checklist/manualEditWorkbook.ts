import type {
    ReconciliationChecklistInvoiceEditItem,
    ReconciliationChecklistMerchantEditItem,
} from "@/api/reconciliationChecklist";
import { formatRawDateTime } from "@/utils/format";
import { downloadFile, loadXlsx } from "./common";
import { MANUAL_EDIT_AMOUNT_COLUMNS } from "./manualEdits";

type ManualEditMode = "invoice" | "merchant";

type ManualEditAmountKey = (typeof MANUAL_EDIT_AMOUNT_COLUMNS)[number]["key"];

export type InvoiceWorkbookRow = ReconciliationChecklistInvoiceEditItem & {
    [key in ManualEditAmountKey]?: string | null;
};

export type MerchantWorkbookRow = ReconciliationChecklistMerchantEditItem & {
    [key in ManualEditAmountKey]?: string | null;
};

const SHARED_HEADERS = ["唯一ID", "子订单号", "结算时间", ...MANUAL_EDIT_AMOUNT_COLUMNS.map((item) => item.label), "收款商家"] as const;
const INVOICE_HEADERS = [...SHARED_HEADERS, "开票时间", "发票号码"] as const;
const MERCHANT_HEADERS = [...SHARED_HEADERS, "应付商家净额", "付款金额", "付款时间（商家）"] as const;

const AMOUNT_LABEL_TO_KEY = Object.fromEntries(MANUAL_EDIT_AMOUNT_COLUMNS.map((item) => [item.label, item.key])) as Record<
    string,
    ManualEditAmountKey
>;

function toCellValue(value: unknown) {
    if (value === null || value === undefined) return "";
    return String(value);
}

function formatExportDateTime(value: string | Date | null | undefined) {
    if (!value) return "";
    const formatted = formatRawDateTime(value);
    return formatted === "-" ? "" : formatted;
}

function commonRowValues(row: InvoiceWorkbookRow | MerchantWorkbookRow) {
    return [
        toCellValue(row.unique_id),
        toCellValue(row.sub_order_no),
        formatExportDateTime(row.settlement_time),
        ...MANUAL_EDIT_AMOUNT_COLUMNS.map((item) => toCellValue(row[item.key])),
        toCellValue(row.receipt_merchant),
    ];
}

export async function exportManualEditWorkbook(
    mode: ManualEditMode,
    rows: InvoiceWorkbookRow[] | MerchantWorkbookRow[],
) {
    const XLSX = await loadXlsx();
    const workbook = XLSX.utils.book_new();
    const headers = mode === "invoice" ? [...INVOICE_HEADERS] : [...MERCHANT_HEADERS];
    const aoa: unknown[][] = [headers];

    for (const row of rows) {
        const shared = commonRowValues(row);
        if (mode === "invoice") {
            const invoiceRow = row as InvoiceWorkbookRow;
            aoa.push([...shared, formatExportDateTime(invoiceRow.invoice_time), toCellValue(invoiceRow.invoice_number)]);
        } else {
            const merchantRow = row as MerchantWorkbookRow;
            aoa.push([
                ...shared,
                toCellValue(merchantRow.merchant_net_amount),
                toCellValue(merchantRow.payment_amount),
                formatExportDateTime(merchantRow.merchant_payment_time),
            ]);
        }
    }

    const worksheet = XLSX.utils.aoa_to_sheet(aoa);
    worksheet["!cols"] = headers.map((header) => ({
        wch: Math.max(12, String(header).length * 2 + 4),
    }));
    XLSX.utils.book_append_sheet(workbook, worksheet, mode === "invoice" ? "发票修改" : "商家修改");
    const buffer = XLSX.write(workbook, { bookType: "xlsx", type: "array" });
    downloadFile(
        new Blob([buffer], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
        mode === "invoice" ? "对账清单发票修改.xlsx" : "对账清单商家修改.xlsx",
    );
}

export async function importInvoiceWorkbook(file: File) {
    const XLSX = await loadXlsx();
    const workbook = XLSX.read(await file.arrayBuffer(), { type: "array" });
    const sheetName = workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];
    const rows = XLSX.utils.sheet_to_json<(string | number | null)[]>(sheet, {
        header: 1,
        raw: false,
        defval: "",
    });
    const [headerRow, ...dataRows] = rows;
    const headerIndex = buildHeaderIndex(headerRow || [], INVOICE_HEADERS);
    return dataRows
        .filter((row) => row.some((cell) => String(cell || "").trim()))
        .map((row) => {
            const result: InvoiceWorkbookRow = {
                unique_id: readCell(row, headerIndex, "唯一ID"),
                sub_order_no: readCell(row, headerIndex, "子订单号"),
                settlement_time: readCell(row, headerIndex, "结算时间") || null,
                receipt_merchant: readCell(row, headerIndex, "收款商家"),
                invoice_time: readCell(row, headerIndex, "开票时间") || null,
                invoice_number: readCell(row, headerIndex, "发票号码"),
            };
            for (const column of MANUAL_EDIT_AMOUNT_COLUMNS) {
                result[column.key] = readCell(row, headerIndex, column.label) || null;
            }
            return result;
        })
        .filter((row) => row.sub_order_no);
}

export async function importMerchantWorkbook(file: File) {
    const XLSX = await loadXlsx();
    const workbook = XLSX.read(await file.arrayBuffer(), { type: "array" });
    const sheetName = workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];
    const rows = XLSX.utils.sheet_to_json<(string | number | null)[]>(sheet, {
        header: 1,
        raw: false,
        defval: "",
    });
    const [headerRow, ...dataRows] = rows;
    const headerIndex = buildHeaderIndex(headerRow || [], MERCHANT_HEADERS);
    return dataRows
        .filter((row) => row.some((cell) => String(cell || "").trim()))
        .map((row) => {
            const result: MerchantWorkbookRow = {
                unique_id: readCell(row, headerIndex, "唯一ID"),
                sub_order_no: readCell(row, headerIndex, "子订单号"),
                settlement_time: readCell(row, headerIndex, "结算时间") || null,
                receipt_merchant: readCell(row, headerIndex, "收款商家"),
                merchant_net_amount: readCell(row, headerIndex, "应付商家净额") || null,
                payment_amount: readCell(row, headerIndex, "付款金额") || null,
                merchant_payment_time: readCell(row, headerIndex, "付款时间（商家）") || null,
            };
            for (const column of MANUAL_EDIT_AMOUNT_COLUMNS) {
                result[column.key] = readCell(row, headerIndex, column.label) || null;
            }
            return result;
        })
        .filter((row) => row.sub_order_no);
}

function buildHeaderIndex(row: (string | number | null)[], requiredHeaders: readonly string[]) {
    const headerIndex = new Map<string, number>();
    row.forEach((cell, index) => {
        const value = String(cell || "").trim();
        if (value) headerIndex.set(value, index);
    });
    const missing = requiredHeaders.filter((header) => !headerIndex.has(header));
    if (missing.length) {
        throw new Error(`缺少模板列：${missing.join("、")}`);
    }
    return headerIndex;
}

function readCell(row: (string | number | null)[], headerIndex: Map<string, number>, header: string) {
    const index = headerIndex.get(header);
    if (index === undefined) return "";
    return String(row[index] || "").trim();
}

export { INVOICE_HEADERS, MERCHANT_HEADERS, AMOUNT_LABEL_TO_KEY };
