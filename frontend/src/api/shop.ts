import { del, downloadBlob, get, post, put, uploadForm } from './index'

export interface Shop {
  id: number
  org_id: number
  org_name?: string | null
  platform_name: string
  shop_name: string
  shop_color?: string
  tax_no?: string
  merchant?: string
  registered_address?: string
  legal_person?: string
  previous_name?: string
  store_long_id?: string
  store_short_id?: string
  settlement_period?: string
  primary_account?: string
  anchor?: string
  shop_type?: string
  purpose?: string
  former_name?: string
  remark?: string
  status: number
  created_at: string
  updated_at?: string
}

export interface ShopForm {
  platform_name: string
  shop_name: string
  shop_color?: string | null
  tax_no?: string | null
  merchant?: string | null
  registered_address?: string | null
  legal_person?: string | null
  previous_name?: string | null
  store_long_id?: string | null
  store_short_id?: string | null
  settlement_period?: string | null
  primary_account?: string | null
  anchor?: string | null
  shop_type?: string | null
  purpose?: string | null
  former_name?: string | null
  remark?: string | null
}

export interface ShopListParams {
  page?: number
  page_size?: number
  keyword?: string
  platform_name?: string
  org_id?: number | string
}

export interface ShopImportError {
  row: number
  message: string
}

export interface ShopImportResult {
  total: number
  created: number
  updated: number
  skipped: number
  errors: ShopImportError[]
}

export function getShopList(params: ShopListParams) {
  return get<{ items: Shop[]; total: number }>('/shops', params as Record<string, any>)
}

export function getShopDetail(id: number) {
  return get<Shop>(`/shops/${id}`)
}

export function createShop(data: ShopForm) {
  return post<Shop>('/shops', data)
}

export function updateShop(id: number, data: Partial<ShopForm> & { status?: number }) {
  return put<Shop>(`/shops/${id}`, data)
}

export function deleteShop(id: number) {
  return del<void>(`/shops/${id}`)
}

export function downloadShopImportTemplate() {
  return downloadBlob('/shops/import-template')
}

export function exportShops(params: ShopListParams & { ids?: string }) {
  return downloadBlob('/shops/export', params as Record<string, any>)
}

export function importShops(file: File) {
  const data = new FormData()
  data.append('file', file)
  return uploadForm<ShopImportResult>('/shops/import', data)
}
