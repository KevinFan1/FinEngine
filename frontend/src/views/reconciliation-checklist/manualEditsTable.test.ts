import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const invoiceSource = readView("invoice-edits.vue");
const merchantSource = readView("merchant-edits.vue");
const manualEditsSource = fs.readFileSync(new URL("./manualEdits.ts", import.meta.url), "utf8");
const workbookSource = fs.readFileSync(new URL("./manualEditWorkbook.ts", import.meta.url), "utf8");

test("manual edit tables use 序号 as the first visible table column", () => {
    for (const [name, source] of [
        ["invoice-edits.vue", invoiceSource],
        ["merchant-edits.vue", merchantSource],
    ] as const) {
        const tableMarkup = firstTable(templateBlock(source));
        const firstColumnLabel = firstTableColumnLabel(tableMarkup);
        assert.equal(firstColumnLabel, "序号", `${name} first table column should be 序号`);
    }
});

test("manual edit pages track missingSubOrderNos in page state", () => {
    for (const source of [invoiceSource, merchantSource]) {
        assert.match(source, /missingSubOrderNos/);
        assert.match(source, /missing_sub_order_nos/);
    }
});

test("manual edit pages drop restored rows without unique id", () => {
    for (const source of [invoiceSource, merchantSource]) {
        assert.match(source, /\.filter\(\(item\) => item\.sub_order_no && item\.unique_id\)/);
        assert.match(source, /hasMissingUniqueId/);
        assert.match(source, /部分数据缺少唯一ID，请重新查询后再保存/);
    }
});

test("manual edit tables use unique_id as row-key", () => {
    for (const source of [invoiceSource, merchantSource]) {
        assert.match(source, /row-key="unique_id"/);
    }
});

test("manual edit pages keep save/export/import actions above the table", () => {
    for (const [name, source] of [
        ["invoice-edits.vue", invoiceSource],
        ["merchant-edits.vue", merchantSource],
    ] as const) {
        assert.match(source, /manual-edit-toolbar/);
        assert.match(source, /上传修改文件/);
        assert.match(source, /导出当前结果/);
        const template = templateBlock(source);
        const toolbarIndex = template.indexOf("manual-edit-toolbar");
        const tableIndex = template.indexOf("<el-table");
        assert.notEqual(toolbarIndex, -1, `${name} should render table toolbar`);
        assert.ok(toolbarIndex < tableIndex, `${name} toolbar should stay above table`);
    }
});

test("manual edit upload buttons stay enabled before querying rows", () => {
    for (const source of [invoiceSource, merchantSource]) {
        assert.doesNotMatch(
            source,
            /:disabled="matchedItems\.length === 0"\s*@click="triggerImport"[\s\S]*?>\s*上传修改文件/,
        );
    }
});

test("manual edit export keeps 唯一ID as the first workbook column", () => {
    assert.match(workbookSource, /const SHARED_HEADERS = \["唯一ID", "子订单号"/);
});

test("manual edit export formats datetime cells without ISO T", () => {
    assert.match(workbookSource, /formatRawDateTime/);
    assert.match(workbookSource, /formatExportDateTime\(row\.settlement_time\)/);
    assert.match(workbookSource, /formatExportDateTime\(invoiceRow\.invoice_time\)/);
    assert.match(workbookSource, /formatExportDateTime\(merchantRow\.merchant_payment_time\)/);
    assert.doesNotMatch(workbookSource, /toCellValue\(row\.settlement_time\)/);
    assert.doesNotMatch(workbookSource, /toCellValue\(invoiceRow\.invoice_time\)/);
    assert.doesNotMatch(workbookSource, /toCellValue\(merchantRow\.merchant_payment_time\)/);
});

test("manual edit upload stores files in OSS before submitting task callbacks", () => {
    assert.match(invoiceSource, /uploadReconciliationChecklistInvoiceEdits/);
    assert.match(merchantSource, /uploadReconciliationChecklistMerchantEdits/);
    assert.match(invoiceSource, /validateManualEditUploadHeaders\(file, CHECKLIST_FILE_TYPE_INVOICE\)/);
    assert.match(merchantSource, /validateManualEditUploadHeaders\(file, CHECKLIST_FILE_TYPE_MERCHANT\)/);
    assert.match(invoiceSource, /callbackReconciliationChecklistInvoiceEditsUpload/);
    assert.match(merchantSource, /callbackReconciliationChecklistMerchantEditsUpload/);
    assert.match(invoiceSource, /uploadFileToOss/);
    assert.match(merchantSource, /uploadFileToOss/);
    assert.match(invoiceSource, /任务中心继续处理/);
    assert.match(merchantSource, /任务中心继续处理/);
    assert.doesNotMatch(invoiceSource, /importInvoiceWorkbook/);
    assert.doesNotMatch(merchantSource, /importMerchantWorkbook/);
});

test("manual edit pages display all required amount columns", () => {
    const labels = [
        "平台补贴",
        "达人补贴",
        "抖音支付补贴",
        "抖音月付营销补贴",
        "银行补贴",
        "用户实付（订单金额）",
        "平台服务费",
        "达人佣金",
        "招商服务费",
    ];
    assert.match(invoiceSource, /MANUAL_EDIT_AMOUNT_COLUMNS/);
    assert.match(merchantSource, /MANUAL_EDIT_AMOUNT_COLUMNS/);
    for (const label of labels) {
        assert.match(manualEditsSource, new RegExp(label));
    }
});

test("manual edit pages format settlement time and compact amount headers", () => {
    for (const source of [invoiceSource, merchantSource]) {
        assert.match(source, /formatRawDateTime\(row\.settlement_time\)/);
        assert.match(source, /column\.shortLabel/);
        assert.match(source, /manual-edit-compact-label/);
    }
});

test("missing sub order alerts stay outside of the table", () => {
    for (const [name, source] of [
        ["invoice-edits.vue", invoiceSource],
        ["merchant-edits.vue", merchantSource],
    ] as const) {
        const template = templateBlock(source);
        const alertIndex = template.indexOf("missingSubOrderNos");
        const tableIndex = template.indexOf("<el-table");
        assert.notEqual(alertIndex, -1, `${name} should render missingSubOrderNos`);
        assert.notEqual(tableIndex, -1, `${name} should render an el-table`);
        assert.ok(alertIndex < tableIndex, `${name} missing sub order prompt should be outside the table`);
    }
});

test("manual edit filter layout keeps organization aligned with the sub order field", () => {
    for (const [name, source] of [
        ["invoice-edits.vue", invoiceSource],
        ["merchant-edits.vue", merchantSource],
    ] as const) {
        assert.match(source, /class="filter-field manual-edit-filter-org"/, `${name} should mark the organization field`);
        assert.match(source, /class="manual-edit-filter-draft-layout"/, `${name} should wrap textarea and actions together`);
        assert.match(source, /grid-template-columns:\s*minmax\(0,\s*1fr\);/, `${name} should let non-admin users use the full width without an empty organization gap`);
        assert.match(source, /\.manual-edit-filter-grid--superadmin\s*{[\s\S]*grid-template-columns:\s*220px minmax\(0,\s*1fr\);/, `${name} should define a dedicated superadmin layout`);
        assert.match(source, /\.manual-edit-filter-grid--superadmin\s*{[\s\S]*grid-template-areas:\s*"org draft";/, `${name} should keep organization and draft fields aligned for admins`);
        assert.match(source, /\.manual-edit-filter-org\s*{\s*grid-area:\s*org;/, `${name} should pin organization field to org area`);
        assert.match(source, /\.manual-edit-filter-draft\s*{\s*grid-area:\s*draft;/, `${name} should pin sub order field to draft area`);
        assert.match(source, /\.manual-edit-filter-draft-layout\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\) auto;/, `${name} should place actions to the right of the textarea`);
        assert.match(source, /\.manual-edit-filter-draft-layout\s*{[\s\S]*grid-template-areas:\s*"textarea actions"\s*"meta \.";/, `${name} should keep meta under the textarea while actions stay beside it`);
        assert.match(source, /\.manual-edit-filter-actions\s*{[\s\S]*grid-area:\s*actions;/, `${name} should pin actions to the textarea action area`);
        assert.match(source, /\.manual-edit-filter-actions\s*{[\s\S]*align-self:\s*end;/, `${name} actions should align with the textarea bottom edge`);
        assert.match(source, /\.manual-edit-filter-meta\s*{[\s\S]*grid-area:\s*meta;/, `${name} meta should stay under the textarea`);
    }
});

test("manual edit pages avoid duplicate empty states between the table and external placeholder", () => {
    for (const [name, source] of [
        ["invoice-edits.vue", invoiceSource],
        ["merchant-edits.vue", merchantSource],
    ] as const) {
        assert.match(source, /<el-table[\s\S]*<template #empty>/, `${name} should define a single table empty slot`);
        assert.match(source, /<el-empty[\s\S]*description="请先输入子订单号并查询"/, `${name} should keep the guided empty state`);
        assert.doesNotMatch(source, /<\/el-table>[\s\S]*<el-empty/, `${name} should not render an extra external empty placeholder`);
    }
});

function readView(filename: string) {
    return fs.readFileSync(new URL(`./${filename}`, import.meta.url), "utf8");
}

function templateBlock(source: string) {
    const start = source.indexOf("<template>");
    const scriptStart = source.indexOf("<script", start);
    const end = source.lastIndexOf("</template>", scriptStart >= 0 ? scriptStart : undefined);
    assert.ok(start >= 0 && end > start, "expected template block");
    return source.slice(start + "<template>".length, end);
}

function firstTable(source: string) {
    const start = source.indexOf("<el-table");
    const end = source.indexOf("</el-table>", start);
    assert.ok(start >= 0 && end > start, "expected first el-table block");
    return source.slice(start, end);
}

function firstTableColumnLabel(tableMarkup: string) {
    const columnMatch = tableMarkup.match(/<el-table-column\b[\s\S]*?label="([^"]+)"/);
    assert.ok(columnMatch, "expected first table column");
    return columnMatch[1];
}
