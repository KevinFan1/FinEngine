import test from "node:test";
import assert from "node:assert/strict";
import { hasMonthSelectionChanged } from "./common.ts";

test("hasMonthSelectionChanged detects selected month updates", () => {
    assert.equal(hasMonthSelectionChanged("", "2026-06"), true);
    assert.equal(hasMonthSelectionChanged("2026-05", "2026-06"), true);
    assert.equal(hasMonthSelectionChanged("2026-06", "2026-06"), false);
    assert.equal(hasMonthSelectionChanged("2026-06", null), true);
    assert.equal(hasMonthSelectionChanged(undefined, ""), false);
});
