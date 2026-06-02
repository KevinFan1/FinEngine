import test from "node:test";
import assert from "node:assert/strict";
import { formatRawDate, formatRawDateTime } from "./format.ts";

test("formatRawDate strips ISO time and timezone suffixes", () => {
    assert.equal(formatRawDate("2026-04-01T00:00:00+08:00"), "2026-04-01");
    assert.equal(formatRawDate("2026-04-01T00:00:00.123456Z"), "2026-04-01");
});

test("formatRawDate keeps already formatted merchant date text", () => {
    assert.equal(formatRawDate("2026-04-01"), "2026-04-01");
    assert.equal(formatRawDate("11月11-20日"), "11月11-20日");
});

test("formatRawDateTime normalizes ISO datetime strings without timezone text", () => {
    assert.equal(formatRawDateTime("2026-01-05T18:22:21"), "2026-01-05 18:22:21");
    assert.equal(formatRawDateTime("2026-01-05T18:22:21.123456+08:00"), "2026-01-05 18:22:21");
});

test("formatRawDateTime keeps non-datetime text and handles empty values", () => {
    assert.equal(formatRawDateTime("11月21-30日"), "11月21-30日");
    assert.equal(formatRawDateTime(null), "-");
});
