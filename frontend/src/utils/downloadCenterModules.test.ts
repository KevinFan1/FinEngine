import test from "node:test";
import assert from "node:assert/strict";
import {
    DOWNLOAD_CENTER_MODULE_OPTIONS,
    getDownloadCenterModuleLabel,
} from "./downloadCenterModules.ts";

test("maps download center modules to the same labels used by the menu", () => {
    assert.equal(getDownloadCenterModuleLabel("summary"), "核算汇总");
    assert.equal(getDownloadCenterModuleLabel("transaction_accounting"), "动账资金核算");
    assert.equal(getDownloadCenterModuleLabel("bic_accounting"), "BIC核算");
    assert.equal(getDownloadCenterModuleLabel("merchant_reconciliation"), "商家对账");
    assert.equal(getDownloadCenterModuleLabel("reconciliation_checklist"), "对账清单");
});

test("exposes aligned filter options for the download center module selector", () => {
    assert.deepEqual(DOWNLOAD_CENTER_MODULE_OPTIONS, [
        { label: "核算汇总", value: "summary" },
        { label: "动账资金核算", value: "transaction_accounting" },
        { label: "BIC核算", value: "bic_accounting" },
        { label: "商家对账", value: "merchant_reconciliation" },
        { label: "对账清单", value: "reconciliation_checklist" },
    ]);
});
