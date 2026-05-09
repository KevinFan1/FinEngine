import { get, post, put, del } from './index'

export interface Shop {
  id: number
  platform_name: string
  shop_name: string
  entity_name?: string
  remark?: string
  status: number
  created_at: string
  updated_at?: string
}

export interface ShopForm {
  platform_name: string
  shop_name: string
  entity_name?: string
  remark?: string
}

export interface ShopListParams {
  page?: number
  page_size?: number
  keyword?: string
  platform_name?: string
}

export function getShopList(params: ShopListParams) {
  return get<{ items: Shop[]; total: number }>('/shops', params as Record<string, any>)
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
