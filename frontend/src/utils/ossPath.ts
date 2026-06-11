import {
    CHECKLIST_FILE_TYPE_INVOICE,
    CHECKLIST_FILE_TYPE_MERCHANT,
    CHECKLIST_FILE_TYPE_SOURCE,
} from "@/views/reconciliation-checklist/common";

const UPLOAD_TYPE_DIR_MAP: Record<string, string> = {
    动账: "dongzhang",
    gmv: "gmv",
    GMV: "gmv",
    bic: "bic",
    运费险: "shipping-insurance",
    订单: "orders",
    其他服务款: "other-service-fee",
    红单: "red-sheet",
    银行流水: "bank-flow",
    对账清单: "reconciliation-checklist",
    [CHECKLIST_FILE_TYPE_SOURCE]: "reconciliation-checklist-source",
    [CHECKLIST_FILE_TYPE_INVOICE]: "reconciliation-checklist-invoice",
    [CHECKLIST_FILE_TYPE_MERCHANT]: "reconciliation-checklist-merchant",
    invoice_edit: "reconciliation-checklist-invoice-edit",
    merchant_edit: "reconciliation-checklist-merchant-edit",
};

function currentOssPeriod(date = new Date()) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    return `${year}${month}`;
}

function sanitizeOssFilename(fileName: string) {
    const safeName = fileName.replace(/[\\/]/g, "_").trim();
    return safeName || "unnamed.xlsx";
}

export function uploadTypeDir(typeName?: string | null) {
    return UPLOAD_TYPE_DIR_MAP[String(typeName || "").trim()] || "misc";
}

export function buildUploadOssKey(prefix: string, typeName: string, fileName: string, uniqueToken?: string | number) {
    const basePrefix = prefix.endsWith("/") ? prefix : `${prefix}/`;
    const token = String(uniqueToken ?? Date.now());
    return `${basePrefix}${uploadTypeDir(typeName)}/${currentOssPeriod()}/${token}_${sanitizeOssFilename(fileName)}`;
}
