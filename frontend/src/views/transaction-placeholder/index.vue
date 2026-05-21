<template>
  <div class="page-container">
    <el-card shadow="never" class="transaction-placeholder-card">
      <section class="placeholder-shell">
        <div class="placeholder-icon">
          <el-icon><Wallet /></el-icon>
        </div>
        <p class="placeholder-kicker">动账资金核算</p>
        <h2>{{ pageTitle }}</h2>
        <p class="placeholder-desc">
          这里预留独立的{{ pageTitle }}页面，后续会接入动账专用接口和处理逻辑。
        </p>
        <div class="placeholder-grid">
          <div class="placeholder-item">
            <span>接口</span>
            <strong>待接入</strong>
          </div>
          <div class="placeholder-item">
            <span>功能</span>
            <strong>占位中</strong>
          </div>
          <div class="placeholder-item">
            <span>数据范围</span>
            <strong>动账资金核算</strong>
          </div>
        </div>
      </section>
    </el-card>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: 'TransactionPlaceholder' })

import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Wallet } from '@element-plus/icons-vue'

const route = useRoute()

const pageTitle = computed(() => (route.meta.title as string) || '动账资金核算')
</script>

<style scoped lang="scss">
.transaction-placeholder-card {
  min-height: calc(100vh - 132px);

  :deep(.el-card__body) {
    min-height: inherit;
    display: grid;
    place-items: center;
    padding: 32px;
  }
}

.placeholder-shell {
  width: min(560px, 100%);
  display: grid;
  justify-items: center;
  text-align: center;
}

.placeholder-icon {
  width: 54px;
  height: 54px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  background: var(--primary-light);
  color: var(--primary);
  font-size: 26px;
  box-shadow: inset 0 0 0 1px var(--primary-light-7);
}

.placeholder-kicker {
  margin-top: 16px;
  color: var(--primary);
  font-size: 12px;
  font-weight: 700;
}

h2 {
  margin: 8px 0 0;
  color: var(--text-primary);
  font-size: 22px;
  font-weight: 700;
  line-height: 1.35;
}

.placeholder-desc {
  max-width: 440px;
  margin-top: 10px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.8;
}

.placeholder-grid {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 22px;
}

.placeholder-item {
  display: grid;
  gap: 5px;
  padding: 12px;
  border: 1px solid var(--border-light);
  border-radius: 10px;
  background: var(--surface-highlight);

  span {
    color: var(--text-tertiary);
    font-size: 12px;
    line-height: 1.2;
  }

  strong {
    color: var(--text-primary);
    font-size: 13px;
    line-height: 1.3;
  }
}

@media (max-width: 640px) {
  .placeholder-grid {
    grid-template-columns: 1fr;
  }
}
</style>
