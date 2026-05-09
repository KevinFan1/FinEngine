import { del, get, post, put } from "./index";

export type SummaryAdjustmentMetric = "gmv" | "return_cost";
export type SummaryAdjustmentDirection = "increase" | "decrease";

export interface SummaryAdjustment {
    id: number;
    org_id: number;
    source_year: number;
    source_month: number;
    platform_name: string;
    shop_id: number;
    shop_name: string;
    metric_key: SummaryAdjustmentMetric;
    metric_label: string;
    direction: SummaryAdjustmentDirection;
    amount: number;
    adjustment_amount: number;
    remark?: string | null;
    created_by: number;
    updated_by?: number | null;
    created_at: string;
    updated_at: string;
}

export interface SummaryAdjustmentListParams {
    source_year: number;
    source_month: number;
    platform_name: string;
    shop_id: number;
    metric_key?: SummaryAdjustmentMetric;
}

export interface SummaryAdjustmentPayload {
    source_year: number;
    source_month: number;
    platform_name: string;
    shop_id: number;
    shop_name: string;
    metric_key: SummaryAdjustmentMetric;
    direction: SummaryAdjustmentDirection;
    amount: number;
    remark?: string;
}

export interface SummaryAdjustmentUpdatePayload {
    metric_key?: SummaryAdjustmentMetric;
    direction?: SummaryAdjustmentDirection;
    amount?: number;
    remark?: string;
}

export function getSummaryAdjustments(params: SummaryAdjustmentListParams) {
    return get<SummaryAdjustment[]>("/summary-adjustments", params);
}

export function createSummaryAdjustment(data: SummaryAdjustmentPayload) {
    return post<SummaryAdjustment>("/summary-adjustments", data);
}

export function updateSummaryAdjustment(id: number, data: SummaryAdjustmentUpdatePayload) {
    return put<SummaryAdjustment>(`/summary-adjustments/${id}`, data);
}

export function deleteSummaryAdjustment(id: number) {
    return del<null>(`/summary-adjustments/${id}`);
}
