import test from "node:test";
import assert from "node:assert/strict";
import {
    monthRangeLabel,
    splitSingleAccountingMonth,
    splitUploadMonthRange,
} from "./common.ts";

test("splitSingleAccountingMonth maps a single month to accounting params", () => {
    assert.deepEqual(splitSingleAccountingMonth("2026-06"), {
        accounting_year: 2026,
        accounting_month: 6,
    });
});

test("splitSingleAccountingMonth ignores empty and invalid values", () => {
    assert.deepEqual(splitSingleAccountingMonth(""), {});
    assert.deepEqual(splitSingleAccountingMonth("bad-input"), {});
});

test("splitUploadMonthRange keeps upload accounting range params", () => {
    assert.deepEqual(splitUploadMonthRange(["2026-01", "2026-03"]), {
        upload_accounting_start_year: 2026,
        upload_accounting_start_month: 1,
        upload_accounting_end_year: 2026,
        upload_accounting_end_month: 3,
    });
});

test("monthRangeLabel returns single month labels directly", () => {
    assert.equal(monthRangeLabel(["2026-06"]), "2026-06");
    assert.equal(monthRangeLabel(["2026-06", "2026-06"]), "2026-06");
});
