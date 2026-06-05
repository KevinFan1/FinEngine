import type { Task } from "../api/task";

export const RECONCILIATION_CHECKLIST_TYPE = "对账清单";
export const ACCOUNTING_UPLOAD_TASK_TYPES = [
    "动账",
    "gmv",
    "bic",
    "运费险",
    "订单",
    "其他服务款",
];
const ACCOUNTING_TASK_TYPE_SET = new Set(ACCOUNTING_UPLOAD_TASK_TYPES);
const ACCOUNTING_RECALCULATE_ONLY_TASK_TYPES = new Set(
    ACCOUNTING_UPLOAD_TASK_TYPES,
);
const MERCHANT_RECONCILIATION_RECALCULATE_ONLY_TASK_TYPES = new Set(["红单"]);

export function buildSingleMonthParams(
    month: string | null | undefined,
    prefix: "source" | "accounting",
) {
    const [yearText, monthText] = String(month || "").split("-");
    const year = Number(yearText) || undefined;
    const monthNumber = Number(monthText) || undefined;

    if (!year || !monthNumber) {
        return {};
    }

    if (prefix === "source") {
        return {
            source_year: year,
            source_month: monthNumber,
        };
    }

    return {
        accounting_year: year,
        accounting_month: monthNumber,
    };
}

export function filterAccountingTasks(tasks: Task[]) {
    return tasks.filter((task) =>
        ACCOUNTING_TASK_TYPE_SET.has(String(task.parsed_type || "")),
    );
}

export function buildAccountingTaskTypes(selectedTypes: string[]) {
    const visibleTypes = selectedTypes.filter((type) =>
        ACCOUNTING_TASK_TYPE_SET.has(type),
    );
    return visibleTypes.length ? visibleTypes.join(",") : undefined;
}

export function isAccountingRecalculateOnlyTaskType(
    taskType: string | null | undefined,
) {
    return ACCOUNTING_RECALCULATE_ONLY_TASK_TYPES.has(String(taskType || ""));
}

export function isMerchantReconciliationRecalculateOnlyTaskType(
    taskType: string | null | undefined,
) {
    return MERCHANT_RECONCILIATION_RECALCULATE_ONLY_TASK_TYPES.has(
        String(taskType || ""),
    );
}
