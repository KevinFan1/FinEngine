<template>
  <span
    class="platform-badge"
    :class="[
      `platform-badge--${platformClass}`,
      `platform-badge--${size}`,
      { 'platform-badge--icon-only': iconOnly },
    ]"
    :title="label"
  >
    <span v-if="iconOnly || showMark" class="platform-badge__mark" aria-hidden="true">
      <img v-if="logoSrc" :src="logoSrc" :alt="label" class="platform-badge__logo" />
      <span v-else>{{ mark }}</span>
    </span>
    <span v-if="!iconOnly" class="platform-badge__label">{{ label }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getPlatformLabel } from '@/utils/format'

const props = withDefaults(defineProps<{
  platform?: string | null
  size?: 'small' | 'default'
  iconOnly?: boolean
  showMark?: boolean
}>(), {
  platform: '',
  size: 'small',
  iconOnly: false,
  showMark: false,
})

const platformClassMap: Record<string, string> = {
  douyin: 'douyin',
  抖音: 'douyin',
  抖店: 'douyin',
  kuaishou: 'kuaishou',
  快手: 'kuaishou',
  xiaohongshu: 'xiaohongshu',
  小红书: 'xiaohongshu',
  weixin_video: 'weixin-video',
  weixinvideo: 'weixin-video',
  'weixin-video': 'weixin-video',
  视频号: 'weixin-video',
  微信小店: 'weixin-video',
  tmall: 'tmall',
  天猫: 'tmall',
  taobao: 'taobao',
  淘宝: 'taobao',
  alipay: 'alipay',
  支付宝: 'alipay',
  qianniu: 'qianniu',
  千牛: 'qianniu',
  miniprogram: 'miniprogram',
  mini_program: 'miniprogram',
  小程序: 'miniprogram',
}

const platformMarkMap: Record<string, string> = {
  douyin: '抖',
  kuaishou: '快',
  xiaohongshu: '红',
  'weixin-video': '微',
  tmall: '天',
  taobao: '淘',
  alipay: '支',
  qianniu: '千',
  miniprogram: '程',
  default: '平',
}

const platformLogoMap: Record<string, string> = {
  douyin: '/brand/platforms/douyin.ico',
  kuaishou: '/brand/platforms/kuaishou.png',
  xiaohongshu: '/brand/platforms/xiaohongshu.png',
  'weixin-video': '/brand/platforms/weixin.ico',
}

const normalizedPlatform = computed(() => String(props.platform || '').trim())

const platformClass = computed(() => {
  const key = normalizedPlatform.value
  return platformClassMap[key] || platformClassMap[key.toLowerCase()] || 'unknown'
})

const label = computed(() => normalizedPlatform.value ? getPlatformLabel(normalizedPlatform.value) : '-')
const mark = computed(() => platformMarkMap[platformClass.value] || platformMarkMap.default)
const logoSrc = computed(() => platformLogoMap[platformClass.value] || '')
</script>

<style scoped lang="scss">
.platform-badge {
  --platform-bg: var(--bg-elevated);
  --platform-border: var(--border-color-light);
  --platform-text: var(--text-secondary);
  --platform-mark-bg: color-mix(in srgb, var(--platform-text) 12%, white);
  --platform-mark-border: transparent;
  --platform-mark-text: var(--platform-text);

  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: fit-content;
  max-width: 100%;
  min-height: 22px;
  padding: 2px 10px 2px 6px;
  border: 1px solid var(--platform-border);
  border-radius: 999px;
  background: var(--platform-bg);
  color: var(--platform-text);
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  vertical-align: middle;
}

.platform-badge__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
  border: 1px solid var(--platform-mark-border);
  border-radius: 999px;
  background: var(--platform-mark-bg);
  color: var(--platform-mark-text);
  font-size: 11px;
  font-weight: 700;
  overflow: hidden;
}

.platform-badge__logo {
  width: 14px;
  height: 14px;
  object-fit: contain;
  display: block;
}

.platform-badge__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.platform-badge--default {
  font-size: 13px;
  min-height: 28px;
  padding: 3px 12px 3px 7px;

  .platform-badge__mark {
    width: 22px;
    height: 22px;
    flex-basis: 22px;
    font-size: 12px;
  }
}

.platform-badge--icon-only {
  padding: 2px;
  gap: 0;
}

.platform-badge--douyin {
  --platform-bg: #f2fbff;
  --platform-border: #90e7f7;
  --platform-text: #161823;
  --platform-mark-bg: #161823;
  --platform-mark-text: #25f4ee;
}

.platform-badge--kuaishou {
  --platform-bg: #fff1e5;
  --platform-border: #ff8a2a;
  --platform-text: #a83b00;
  --platform-mark-bg: #ffffff;
  --platform-mark-border: #ff6a00;
  --platform-mark-text: #fff7ed;
}

.platform-badge--xiaohongshu {
  --platform-bg: #fff0f3;
  --platform-border: #ff9db2;
  --platform-text: #d7002a;
  --platform-mark-bg: #ff2442;
  --platform-mark-text: #fff5f7;
}

.platform-badge--weixin-video,
.platform-badge--miniprogram {
  --platform-bg: #e7f8ef;
  --platform-border: #48d987;
  --platform-text: #046b32;
  --platform-mark-bg: #ffffff;
  --platform-mark-border: #07c160;
  --platform-mark-text: #f4fff8;
}

.platform-badge--taobao {
  --platform-bg: #fff5eb;
  --platform-border: #ffbc80;
  --platform-text: #d45a00;
  --platform-mark-bg: #ff5000;
  --platform-mark-text: #fff8f0;
}

.platform-badge--alipay {
  --platform-bg: #edf6ff;
  --platform-border: #9fd0ff;
  --platform-text: #1266d6;
  --platform-mark-bg: #1677ff;
  --platform-mark-text: #f7fbff;
}

.platform-badge--qianniu {
  --platform-bg: #fff8e7;
  --platform-border: #f2c759;
  --platform-text: #a06000;
  --platform-mark-bg: #f2a900;
  --platform-mark-text: #fff9e8;
}

.platform-badge--tmall {
  --platform-bg: #fff0f4;
  --platform-border: #ff9fb5;
  --platform-text: #d0002c;
  --platform-mark-bg: #ff0036;
  --platform-mark-text: #fff5f8;
}

.platform-badge--unknown {
  --platform-bg: var(--bg-elevated);
  --platform-border: var(--border-color-light);
  --platform-text: var(--text-secondary);
  --platform-mark-bg: var(--bg-card);
  --platform-mark-border: transparent;
  --platform-mark-text: var(--text-tertiary);
}

:global(html.dark) .platform-badge {
  --platform-bg: rgba(148, 163, 184, 0.08);
  --platform-border: rgba(148, 163, 184, 0.18);
  --platform-text: var(--text-secondary);
  --platform-mark-bg: rgba(15, 23, 42, 0.36);
  --platform-mark-border: transparent;
  --platform-mark-text: var(--text-tertiary);
}

:global(html.dark) .platform-badge--douyin {
  --platform-bg: rgba(37, 244, 238, 0.13);
  --platform-border: rgba(37, 244, 238, 0.34);
  --platform-text: #b9fbf8;
  --platform-mark-bg: #161823;
  --platform-mark-text: #25f4ee;
}

:global(html.dark) .platform-badge--kuaishou {
  --platform-bg: rgba(255, 106, 0, 0.18);
  --platform-border: rgba(255, 138, 42, 0.52);
  --platform-text: #ffd0a8;
  --platform-mark-bg: #fff7ed;
  --platform-mark-border: #ff8a2a;
  --platform-mark-text: #fff7ed;
}

:global(html.dark) .platform-badge--xiaohongshu {
  --platform-bg: rgba(255, 36, 66, 0.15);
  --platform-border: rgba(255, 122, 145, 0.36);
  --platform-text: #ffb8c5;
  --platform-mark-bg: #ff2442;
  --platform-mark-text: #fff5f7;
}

:global(html.dark) .platform-badge--weixin-video,
:global(html.dark) .platform-badge--miniprogram {
  --platform-bg: rgba(7, 193, 96, 0.17);
  --platform-border: rgba(72, 217, 135, 0.5);
  --platform-text: #b9f5d1;
  --platform-mark-bg: #f4fff8;
  --platform-mark-border: #48d987;
  --platform-mark-text: #f4fff8;
}

:global(html.dark) .platform-badge--taobao {
  --platform-bg: rgba(255, 80, 0, 0.15);
  --platform-border: rgba(255, 149, 84, 0.36);
  --platform-text: #ffc19c;
  --platform-mark-bg: #ff5000;
  --platform-mark-text: #fff8f0;
}

:global(html.dark) .platform-badge--alipay {
  --platform-bg: rgba(22, 119, 255, 0.15);
  --platform-border: rgba(97, 164, 255, 0.36);
  --platform-text: #b7d7ff;
  --platform-mark-bg: #1677ff;
  --platform-mark-text: #f7fbff;
}

:global(html.dark) .platform-badge--qianniu {
  --platform-bg: rgba(242, 169, 0, 0.15);
  --platform-border: rgba(242, 199, 89, 0.36);
  --platform-text: #f8d77b;
  --platform-mark-bg: #f2a900;
  --platform-mark-text: #fff9e8;
}

:global(html.dark) .platform-badge--tmall {
  --platform-bg: rgba(255, 0, 54, 0.15);
  --platform-border: rgba(255, 120, 148, 0.36);
  --platform-text: #ffb8c8;
  --platform-mark-bg: #ff0036;
  --platform-mark-text: #fff5f8;
}
</style>
