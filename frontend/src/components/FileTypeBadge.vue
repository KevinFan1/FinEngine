<template>
  <span
    class="file-type-badge"
    :class="[
      `file-type-badge--${typeClass}`,
      `file-type-badge--${size}`,
      { 'file-type-badge--icon-only': iconOnly },
    ]"
    :title="label"
  >
    <span v-if="iconOnly || showMark" class="file-type-badge__mark" aria-hidden="true">{{ mark }}</span>
    <span v-if="!iconOnly" class="file-type-badge__label">{{ label }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  type?: string | null
  size?: 'small' | 'default'
  iconOnly?: boolean
  showMark?: boolean
}>(), {
  type: '',
  size: 'small',
  iconOnly: false,
  showMark: false,
})

const typeMap: Record<string, { label: string; typeClass: string; mark: string }> = {
  动账: { label: '动账', typeClass: 'ledger', mark: '账' },
  gmv: { label: 'GMV', typeClass: 'gmv', mark: 'G' },
  GMV: { label: 'GMV', typeClass: 'gmv', mark: 'G' },
  bic: { label: 'BIC', typeClass: 'bic', mark: 'B' },
  BIC: { label: 'BIC', typeClass: 'bic', mark: 'B' },
  运费险: { label: '运费险', typeClass: 'insurance', mark: '险' },
  订单: { label: '订单', typeClass: 'order', mark: '单' },
  其他服务款: { label: '其他服务款', typeClass: 'service', mark: '服' },
  红单: { label: '红单', typeClass: 'red-sheet', mark: '红' },
  银行流水: { label: '银行流水', typeClass: 'bank-flow', mark: '银' },
}

const normalizedType = computed(() => String(props.type || '').trim())
const meta = computed(() => typeMap[normalizedType.value] || typeMap[normalizedType.value.toLowerCase()] || {
  label: normalizedType.value || '-',
  typeClass: 'unknown',
  mark: '类',
})

const label = computed(() => meta.value.label)
const mark = computed(() => meta.value.mark)
const typeClass = computed(() => meta.value.typeClass)
</script>

<style scoped lang="scss">
.file-type-badge {
  --type-bg: var(--bg-elevated);
  --type-border: var(--border-color-light);
  --type-text: var(--text-secondary);
  --type-mark-bg: var(--bg-card);
  --type-mark-text: var(--text-tertiary);

  display: inline-flex;
  align-items: center;
  gap: 5px;
  width: fit-content;
  max-width: 100%;
  min-height: 22px;
  padding: 2px 8px;
  border: 1px solid var(--type-border);
  border-radius: 6px;
  background: var(--type-bg);
  color: var(--type-text);
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  vertical-align: middle;
}

.file-type-badge__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex: 0 0 16px;
  border: 1px solid var(--type-border);
  border-radius: 3px;
  background: var(--type-mark-bg);
  color: var(--type-mark-text);
  font-size: 11px;
  font-weight: 700;
  box-shadow: none;
}

.file-type-badge__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-type-badge--default {
  font-size: 13px;
  min-height: 26px;
  padding: 3px 10px;

  .file-type-badge__mark {
    width: 18px;
    height: 18px;
    flex-basis: 18px;
    font-size: 12px;
  }
}

.file-type-badge--icon-only {
  padding: 2px;
  gap: 0;
}

.file-type-badge--ledger {
  --type-bg: #eef2ff;
  --type-border: #c7d2fe;
  --type-text: #3730a3;
  --type-mark-bg: #e0e7ff;
  --type-mark-text: #312e81;
}

.file-type-badge--gmv {
  --type-bg: #ecfdf5;
  --type-border: #bbf7d0;
  --type-text: #047857;
  --type-mark-bg: #dcfce7;
  --type-mark-text: #065f46;
}

.file-type-badge--bic {
  --type-bg: #eff6ff;
  --type-border: #bfdbfe;
  --type-text: #1d4ed8;
  --type-mark-bg: #dbeafe;
  --type-mark-text: #1e40af;
}

.file-type-badge--insurance {
  --type-bg: #f0fdfa;
  --type-border: #99f6e4;
  --type-text: #0f766e;
  --type-mark-bg: #ccfbf1;
  --type-mark-text: #115e59;
}

.file-type-badge--order {
  --type-bg: #fff7ed;
  --type-border: #fed7aa;
  --type-text: #9a3412;
  --type-mark-bg: #ffedd5;
  --type-mark-text: #7c2d12;
}

.file-type-badge--service {
  --type-bg: #faf5ff;
  --type-border: #e9d5ff;
  --type-text: #7e22ce;
  --type-mark-bg: #f3e8ff;
  --type-mark-text: #6b21a8;
}

.file-type-badge--red-sheet {
  --type-bg: #fff1f2;
  --type-border: #fecdd3;
  --type-text: #be123c;
  --type-mark-bg: #ffe4e6;
  --type-mark-text: #9f1239;
}

.file-type-badge--bank-flow {
  --type-bg: #f0f9ff;
  --type-border: #bae6fd;
  --type-text: #0369a1;
  --type-mark-bg: #e0f2fe;
  --type-mark-text: #075985;
}

.file-type-badge--unknown {
  --type-bg: var(--bg-elevated);
  --type-border: var(--border-color-light);
  --type-text: var(--text-secondary);
  --type-mark-bg: var(--bg-card);
  --type-mark-text: var(--text-tertiary);
}

:global(html.dark) .file-type-badge {
  --type-bg: rgba(148, 163, 184, 0.08);
  --type-border: rgba(148, 163, 184, 0.18);
  --type-text: var(--text-secondary);
  --type-mark-bg: rgba(15, 23, 42, 0.36);
  --type-mark-text: var(--text-tertiary);
}

:global(html.dark) .file-type-badge--ledger {
  --type-bg: rgba(99, 102, 241, 0.16);
  --type-border: rgba(129, 140, 248, 0.36);
  --type-text: #c7d2fe;
  --type-mark-bg: rgba(99, 102, 241, 0.22);
  --type-mark-text: #e0e7ff;
}

:global(html.dark) .file-type-badge--gmv {
  --type-bg: rgba(16, 185, 129, 0.14);
  --type-border: rgba(52, 211, 153, 0.34);
  --type-text: #bbf7d0;
  --type-mark-bg: rgba(16, 185, 129, 0.2);
  --type-mark-text: #dcfce7;
}

:global(html.dark) .file-type-badge--bic {
  --type-bg: rgba(59, 130, 246, 0.15);
  --type-border: rgba(96, 165, 250, 0.34);
  --type-text: #bfdbfe;
  --type-mark-bg: rgba(59, 130, 246, 0.21);
  --type-mark-text: #dbeafe;
}

:global(html.dark) .file-type-badge--insurance {
  --type-bg: rgba(20, 184, 166, 0.14);
  --type-border: rgba(45, 212, 191, 0.34);
  --type-text: #99f6e4;
  --type-mark-bg: rgba(20, 184, 166, 0.2);
  --type-mark-text: #ccfbf1;
}

:global(html.dark) .file-type-badge--order {
  --type-bg: rgba(249, 115, 22, 0.15);
  --type-border: rgba(251, 146, 60, 0.34);
  --type-text: #fed7aa;
  --type-mark-bg: rgba(249, 115, 22, 0.2);
  --type-mark-text: #ffedd5;
}

:global(html.dark) .file-type-badge--service {
  --type-bg: rgba(168, 85, 247, 0.15);
  --type-border: rgba(192, 132, 252, 0.35);
  --type-text: #e9d5ff;
  --type-mark-bg: rgba(168, 85, 247, 0.2);
  --type-mark-text: #f3e8ff;
}

:global(html.dark) .file-type-badge--red-sheet {
  --type-bg: rgba(244, 63, 94, 0.15);
  --type-border: rgba(251, 113, 133, 0.34);
  --type-text: #fecdd3;
  --type-mark-bg: rgba(244, 63, 94, 0.21);
  --type-mark-text: #ffe4e6;
}

:global(html.dark) .file-type-badge--bank-flow {
  --type-bg: rgba(14, 165, 233, 0.15);
  --type-border: rgba(56, 189, 248, 0.34);
  --type-text: #bae6fd;
  --type-mark-bg: rgba(14, 165, 233, 0.21);
  --type-mark-text: #e0f2fe;
}
</style>
