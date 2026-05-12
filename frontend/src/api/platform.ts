import { get, put } from './index'

export interface Platform {
  id: number
  code: string
  name: string
  parent_code?: string | null
  processor_code?: string | null
  order_scope_code?: string | null
  sort_order: number
  status: number
  created_at: string
}

/**
 * Get all platforms
 */
export function getPlatformList() {
  return get<Platform[]>('/platforms')
}

/**
 * Update platform config
 */
export function updatePlatform(id: number, data: Partial<Platform>) {
  return put<Platform>(`/platforms/${id}`, data)
}
