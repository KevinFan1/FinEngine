import { get } from './index'
import type { PaginatedData } from './index'

export interface AuditLog {
  id: number
  user_id: number
  org_id?: number
  org_name?: string
  username: string
  display_name?: string
  module: string
  action: string
  description: string
  ip?: string
  ip_address?: string
  user_agent?: string
  status: string
  error_msg?: string
  created_at: string
}

export interface AuditLogListParams {
  page?: number
  page_size?: number
  org_id?: number | string
  module?: string
  action?: string
  username?: string
  start_time?: string
  end_time?: string
}

/**
 * Get audit log list
 */
export function getAuditLogList(params: AuditLogListParams) {
  return get<PaginatedData<AuditLog>>('/audit-logs', params)
}

/**
 * Export audit logs
 */
export function exportAuditLogs(params: AuditLogListParams) {
  return get<{ download_url: string }>('/audit-logs/export', params)
}
