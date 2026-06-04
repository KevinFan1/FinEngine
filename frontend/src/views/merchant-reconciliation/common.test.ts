import test from "node:test";
import assert from "node:assert/strict";
import { hasMonthSelectionChanged, merchantReconciliationShopListParams } from "./common.ts";

test("hasMonthSelectionChanged detects selected month updates", () => {
    assert.equal(hasMonthSelectionChanged("", "2026-06"), true);
    assert.equal(hasMonthSelectionChanged("2026-05", "2026-06"), true);
    assert.equal(hasMonthSelectionChanged("2026-06", "2026-06"), false);
    assert.equal(hasMonthSelectionChanged("2026-06", null), true);
    assert.equal(hasMonthSelectionChanged(undefined, ""), false);
});

test("merchant reconciliation shop params do not lock platform display name", () => {
    assert.deepEqual(merchantReconciliationShopListParams(2), {
        page: 1,
        page_size: 1000,
        org_id: 2,
    });
    assert.equal("platform_name" in merchantReconciliationShopListParams(2), false);
});
