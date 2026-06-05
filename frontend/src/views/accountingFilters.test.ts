import test from "node:test";
import assert from "node:assert/strict";
import type { Task } from "../api/task";
import {
    ACCOUNTING_UPLOAD_TASK_TYPES,
    RECONCILIATION_CHECKLIST_TYPE,
    buildAccountingTaskTypes,
    buildSingleMonthParams,
    filterAccountingTasks,
    isAccountingRecalculateOnlyTaskType,
    isMerchantReconciliationRecalculateOnlyTaskType,
} from "./accountingFilters.ts";

test("buildSingleMonthParams maps a single source month to API params", () => {
    assert.deepEqual(buildSingleMonthParams("2026-05", "source"), {
        source_year: 2026,
        source_month: 5,
    });
});

test("buildSingleMonthParams maps a single accounting month to API params", () => {
    assert.deepEqual(buildSingleMonthParams("2026-06", "accounting"), {
        accounting_year: 2026,
        accounting_month: 6,
    });
});

test("buildSingleMonthParams ignores empty and invalid month values", () => {
    assert.deepEqual(buildSingleMonthParams("", "source"), {});
    assert.deepEqual(buildSingleMonthParams("bad-input", "accounting"), {});
});

test("filterAccountingTasks removes reconciliation checklist tasks", () => {
    const tasks = [
        { id: 1, status: "success", progress: 100, error_message: null, error_reason: null, created_at: "2026-06-05", parsed_type: "动账" },
        { id: 2, status: "success", progress: 100, error_message: null, error_reason: null, created_at: "2026-06-05", parsed_type: "红单" },
        { id: 3, status: "success", progress: 100, error_message: null, error_reason: null, created_at: "2026-06-05", parsed_type: "银行流水" },
        { id: 4, status: "success", progress: 100, error_message: null, error_reason: null, created_at: "2026-06-05", parsed_type: RECONCILIATION_CHECKLIST_TYPE },
    ] satisfies Task[];

    assert.deepEqual(
        filterAccountingTasks(tasks).map((item) => item.id),
        [1],
    );
});

test("buildAccountingTaskTypes excludes reconciliation checklist from task filters", () => {
    assert.equal(
        buildAccountingTaskTypes(["动账", RECONCILIATION_CHECKLIST_TYPE, "订单"]),
        "动账,订单",
    );
    assert.equal(
        buildAccountingTaskTypes(["动账", "红单", "银行流水", "订单"]),
        "动账,订单",
    );
    assert.equal(
        buildAccountingTaskTypes([RECONCILIATION_CHECKLIST_TYPE]),
        undefined,
    );
});

test("ACCOUNTING_UPLOAD_TASK_TYPES matches accounting upload center supported types", () => {
    assert.deepEqual(ACCOUNTING_UPLOAD_TASK_TYPES, [
        "动账",
        "gmv",
        "bic",
        "运费险",
        "订单",
        "其他服务款",
    ]);
});

test("isAccountingRecalculateOnlyTaskType keeps ordinary accounting tasks on recalculate only", () => {
    assert.equal(isAccountingRecalculateOnlyTaskType("动账"), true);
    assert.equal(isAccountingRecalculateOnlyTaskType("gmv"), true);
    assert.equal(isAccountingRecalculateOnlyTaskType("bic"), true);
    assert.equal(isAccountingRecalculateOnlyTaskType("运费险"), true);
    assert.equal(isAccountingRecalculateOnlyTaskType("订单"), true);
    assert.equal(isAccountingRecalculateOnlyTaskType("其他服务款"), true);
    assert.equal(isAccountingRecalculateOnlyTaskType("红单"), false);
    assert.equal(isAccountingRecalculateOnlyTaskType("银行流水"), false);
    assert.equal(
        isAccountingRecalculateOnlyTaskType(RECONCILIATION_CHECKLIST_TYPE),
        false,
    );
});

test("isMerchantReconciliationRecalculateOnlyTaskType only hides retry for red-sheet tasks", () => {
    assert.equal(
        isMerchantReconciliationRecalculateOnlyTaskType("红单"),
        true,
    );
    assert.equal(
        isMerchantReconciliationRecalculateOnlyTaskType("银行流水"),
        false,
    );
    assert.equal(
        isMerchantReconciliationRecalculateOnlyTaskType("动账"),
        false,
    );
});
