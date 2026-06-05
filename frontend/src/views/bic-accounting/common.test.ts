import test from "node:test";
import assert from "node:assert/strict";
import {
    monthRangeLabel,
    splitMonthRange,
    splitSingleAccountingMonth,
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

test("splitMonthRange keeps accounting range params for range-based pages", () => {
    assert.deepEqual(splitMonthRange(["2026-01", "2026-03"]), {
        accounting_start_year: 2026,
        accounting_start_month: 1,
        accounting_end_year: 2026,
        accounting_end_month: 3,
    });
});

test("monthRangeLabel returns single month labels directly", () => {
    assert.equal(monthRangeLabel(["2026-06"]), "2026-06");
    assert.equal(monthRangeLabel(["2026-06", "2026-06"]), "2026-06");
});
