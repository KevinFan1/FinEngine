import type { Platform } from '@/api/platform'

export interface PlatformOption {
  label: string
  value: string
  parent?: string
}

const fallbackPlatforms: Platform[] = [
  { id: 0, code: 'douyin', name: '抖音', parent_code: 'douyin', processor_code: 'douyin', order_scope_code: 'douyin', sort_order: 1, status: 1, created_at: '' },
  { id: 0, code: 'kuaishou', name: '快手', parent_code: 'kuaishou', processor_code: 'kuaishou', order_scope_code: 'kuaishou', sort_order: 2, status: 1, created_at: '' },
  { id: 0, code: 'xiaohongshu', name: '小红书', parent_code: 'xiaohongshu', processor_code: 'xiaohongshu', order_scope_code: 'xiaohongshu', sort_order: 3, status: 1, created_at: '' },
  { id: 0, code: 'weixin_video', name: '微信小店', parent_code: 'weixin_video', processor_code: 'weixin_video', order_scope_code: 'weixin_video', sort_order: 4, status: 1, created_at: '' },
  { id: 0, code: 'taobao', name: '淘宝', parent_code: 'taobao', processor_code: 'taobao', order_scope_code: 'taobao', sort_order: 5, status: 1, created_at: '' },
  { id: 0, code: 'alipay', name: '支付宝', parent_code: 'taobao', processor_code: 'alipay', order_scope_code: 'taobao', sort_order: 6, status: 1, created_at: '' },
  { id: 0, code: 'qianniu', name: '千牛', parent_code: 'taobao', processor_code: 'qianniu', order_scope_code: 'taobao', sort_order: 7, status: 1, created_at: '' },
  { id: 0, code: 'tmall', name: '天猫', parent_code: 'taobao', processor_code: 'tmall', order_scope_code: 'taobao', sort_order: 8, status: 1, created_at: '' },
  { id: 0, code: 'miniprogram', name: '小程序', parent_code: 'miniprogram', processor_code: 'miniprogram', order_scope_code: 'miniprogram', sort_order: 9, status: 1, created_at: '' },
]

export function getFallbackPlatforms() {
  return fallbackPlatforms
}

export function toSourcePlatformOptions(platforms: Platform[] = fallbackPlatforms): PlatformOption[] {
  return platforms
    .filter((platform) => platform.status !== 0)
    .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
    .map((platform) => ({
      label: platform.name,
      value: platform.code,
      parent: platform.parent_code || platform.code,
    }))
}

export function toReportPlatformOptions(platforms: Platform[] = fallbackPlatforms): PlatformOption[] {
  const byCode = new Map(platforms.map((platform) => [platform.code, platform]))
  const seen = new Set<string>()
  const options: PlatformOption[] = []

  platforms
    .filter((platform) => platform.status !== 0)
    .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
    .forEach((platform) => {
      const reportCode = platform.parent_code || platform.code
      if (seen.has(reportCode)) return
      seen.add(reportCode)
      const reportPlatform = byCode.get(reportCode)
      options.push({
        label: reportPlatform?.name || platform.name,
        value: reportCode,
        parent: reportCode,
      })
    })

  return options
}

export function getReportPlatformCode(platformCode: string | null | undefined, platforms: Platform[] = fallbackPlatforms) {
  if (!platformCode) return ''
  return platforms.find((platform) => platform.code === platformCode)?.parent_code || platformCode
}
