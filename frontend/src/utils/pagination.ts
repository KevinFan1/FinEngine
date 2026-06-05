export const DEFAULT_PAGE_SIZE = 20

export const PAGE_SIZE_OPTIONS = [20, 50, 100]

export const PAGINATION_LAYOUT = 'total, sizes, prev, pager, next, jumper'

export const LIGHT_PAGINATION_LAYOUT = 'sizes, prev, pager, next'

export function visiblePaginationTotal(
  total: number | null | undefined,
  page: number,
  pageSize: number,
  itemCount: number,
) {
  if (total != null) return total
  const currentEnd = Math.max(page - 1, 0) * pageSize + itemCount
  return itemCount >= pageSize ? currentEnd + 1 : currentEnd
}
