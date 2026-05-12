import { get, post, put } from './index'
import type { PaginatedData } from './index'

export interface User {
  id: number
  username: string
  display_name: string
  phone: string
  email: string
  role: string
  org_id: number | null
  org_name?: string
  status: string
  last_login_at: string | null
  created_at: string
}

export interface UserListParams {
  page?: number
  page_size?: number
  keyword?: string
  org_id?: number | string
  role?: string
  status?: string
}

export interface UserForm {
  username: string
  phone: string
  password?: string
  display_name: string
  email?: string
  role: string
  org_id: number | null
}

/**
 * Get user list
 */
export function getUserList(params: UserListParams) {
  return get<PaginatedData<User>>('/users', params)
}

/**
 * Create user
 */
export function createUser(data: UserForm) {
  return post<User>('/users', data)
}

/**
 * Update user
 */
export function updateUser(id: number, data: Partial<UserForm>) {
  return put<User>(`/users/${id}`, data)
}

/**
 * Reset user password
 */
export function resetUserPassword(id: number) {
  return post<{ password: string }>(`/users/${id}/reset-pwd`)
}

/**
 * Toggle user status (enable/disable)
 */
export function toggleUserStatus(id: number, status: string) {
  return put<User>(`/users/${id}`, { status })
}
