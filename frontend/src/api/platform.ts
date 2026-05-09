import { get, put } from './index'

export interface Platform {
  id: number
  code: string
  name: string
  enabled: boolean
  config: Record<string, any>
  created_at: string
  updated_at: string
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
