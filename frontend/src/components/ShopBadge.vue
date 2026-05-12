<template>
  <span
    class="shop-badge"
    :class="`shop-badge--${size}`"
    :style="badgeStyle"
    :title="label"
  >
    <span class="shop-badge__dot"></span>
    <span class="shop-badge__label">{{ label }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  label?: string | null
  color?: string | null
  size?: 'default' | 'compact' | 'table'
}>(), {
  label: '',
  color: '',
  size: 'default',
})

function normalizeHexColor(value?: string | null) {
  const color = String(value || '').trim()
  if (!color) return '#CBD5E1'
  return color.startsWith('#') ? color : `#${color}`
}

function fallbackColor(text: string) {
  const palette = ['#F59E0B', '#38BDF8', '#F97316', '#14B8A6', '#FB7185', '#C084FC', '#84CC16', '#06B6D4', '#F43F5E', '#A78BFA']
  let hash = 0
  for (const char of text) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0
  }
  return palette[hash % palette.length]
}

const label = computed(() => String(props.label || '-'))
const normalizedColor = computed(() => normalizeHexColor(props.color || fallbackColor(label.value)))
const badgeStyle = computed(() => ({
  '--shop-badge-color': normalizedColor.value,
  '--shop-badge-bg': `color-mix(in srgb, ${normalizedColor.value} 12%, white)`,
  '--shop-badge-border': `color-mix(in srgb, ${normalizedColor.value} 30%, white)`,
  '--shop-badge-text': `color-mix(in srgb, ${normalizedColor.value} 86%, #1f2937)`,
}))
</script>

<style scoped lang="scss">
.shop-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  min-height: 22px;
  padding: 0 10px;
  border: 1px solid var(--shop-badge-border);
  border-radius: 999px;
  background: var(--shop-badge-bg);
  color: var(--shop-badge-text);
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  vertical-align: middle;
}

.shop-badge__dot {
  width: 8px;
  height: 8px;
  flex: 0 0 8px;
  border-radius: 50%;
  background: var(--shop-badge-color);
}

.shop-badge__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shop-badge--compact {
  gap: 5px;
  min-height: 20px;
  max-width: 168px;
  padding: 0 8px;
  font-size: 12px;

  .shop-badge__dot {
    width: 6px;
    height: 6px;
    flex-basis: 6px;
  }
}

.shop-badge--table {
  gap: 5px;
  min-height: 20px;
  max-width: 100%;
  padding: 0 8px;
  border-color: color-mix(in srgb, var(--shop-badge-color) 22%, white);
  background: color-mix(in srgb, var(--shop-badge-color) 8%, white);
  font-size: 12px;
  font-weight: 500;

  .shop-badge__dot {
    width: 6px;
    height: 6px;
    flex-basis: 6px;
  }
}
</style>
