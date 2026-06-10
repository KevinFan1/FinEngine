export const DOWNLOAD_CENTER_MODULE_OPTIONS = [
    { label: "核算汇总", value: "summary" },
    { label: "动账资金核算", value: "transaction_accounting" },
    { label: "BIC核算", value: "bic_accounting" },
    { label: "商家对账", value: "merchant_reconciliation" },
    { label: "对账清单", value: "reconciliation_checklist" },
] as const;

const DOWNLOAD_CENTER_MODULE_LABELS = Object.fromEntries(
    DOWNLOAD_CENTER_MODULE_OPTIONS.map((option) => [option.value, option.label]),
) as Record<string, string>;

export function getDownloadCenterModuleLabel(module: string) {
    return DOWNLOAD_CENTER_MODULE_LABELS[module] || module;
}
