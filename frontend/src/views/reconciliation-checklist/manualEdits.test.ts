import test from "node:test";
import assert from "node:assert/strict";
import {
    MANUAL_EDIT_MAX_SUB_ORDERS,
    MANUAL_EDIT_STATE_KEYS,
    manualEditLimitMessage,
    parseManualEditSubOrders,
} from "./manualEdits.ts";

test("parseManualEditSubOrders trims, deduplicates, and preserves order", () => {
    assert.deepEqual(
        parseManualEditSubOrders("  SO-001 \nSO-002, SO-001，SO-003\n\nSO-002  ,  "),
        ["SO-001", "SO-002", "SO-003"],
    );
});

test("manual edit max sub order limit stays at 100", () => {
    assert.equal(MANUAL_EDIT_MAX_SUB_ORDERS, 100);
    assert.equal(
        manualEditLimitMessage(101),
        "已识别 101 个子订单号，单次最多查询 100 个子订单号",
    );
});

test("manual edit state keys remain stable", () => {
    assert.deepEqual(MANUAL_EDIT_STATE_KEYS, {
        invoice: "reconciliation-checklist:invoice-edits",
        merchant: "reconciliation-checklist:merchant-edits",
    });
});

test("checklist header compatibility maps 系统行定位值 to 唯一ID", async () => {
    const common = await import("./common.ts");
    assert.equal(common.canonicalChecklistHeader("系统行定位值"), "唯一ID");
});

test("manual edit upload headers require 唯一ID", async () => {
    const common = await import("./common.ts");

    const invoiceResult = common.validateChecklistHeadersForFileType(
        ["子订单号", "收款商家", "开票时间", "发票号码"],
        common.CHECKLIST_FILE_TYPE_INVOICE,
    );
    const merchantResult = common.validateChecklistHeadersForFileType(
        ["子订单号", "收款商家", "应付商家净额", "付款金额", "付款时间（商家）"],
        common.CHECKLIST_FILE_TYPE_MERCHANT,
    );

    assert.equal(invoiceResult.valid, false);
    assert.deepEqual(invoiceResult.missing, ["唯一ID"]);
    assert.equal(merchantResult.valid, false);
    assert.deepEqual(merchantResult.missing, ["唯一ID"]);
});
