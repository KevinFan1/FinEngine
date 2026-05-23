<template>
  <div class="page-container dashboard-page">
    <section class="dashboard-summary">
      <div class="summary-main">
        <div class="summary-kicker">
          <span class="status-dot" :class="statusDotClass"></span>
          财务工作台
        </div>
        <h2>工作台</h2>
        <div class="summary-meta">
          <span>{{ userStore.displayName }}</span>
          <span v-if="userStore.userInfo?.org_name">{{ userStore.userInfo.org_name }}</span>
          <span>{{ roleLabel }}</span>
        </div>
      </div>

      <div class="summary-actions">
        <el-button type="primary" @click="router.push('/upload')">
          <el-icon><Upload /></el-icon>
          上传文件
        </el-button>
        <el-button @click="router.push('/summary-report')">
          <el-icon><DataAnalysis /></el-icon>
          查看报表
        </el-button>
      </div>
    </section>

    <section class="metric-strip">
      <button
        v-for="metric in taskMetrics"
        :key="metric.label"
        type="button"
        class="metric-cell"
        :class="metric.className"
        @click="router.push(metric.path)"
      >
        <div>
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
        </div>
        <small>{{ metric.hint }}</small>
      </button>
    </section>

    <section class="dashboard-board">
      <el-card shadow="never" class="status-card">
        <template #header>
          <div class="card-header">
            <span class="card-header-title">任务状态</span>
            <el-button link type="primary" @click="router.push('/tasks')">任务列表</el-button>
          </div>
        </template>
        <div class="status-panel">
          <div class="status-head">
            <span>当前状态</span>
            <strong :class="healthClass">{{ healthLabel }}</strong>
          </div>
          <div class="health-bar">
            <span :style="{ width: completionRate }"></span>
          </div>
          <div class="status-foot">
            <span>总任务 {{ totalTasks }}</span>
            <span>待处理 {{ pendingTasks }}</span>
            <span>失败 {{ failedTasks }}</span>
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="shortcut-card">
        <template #header>
          <span class="card-header-title">常用操作</span>
        </template>
        <div class="shortcut-list">
          <button
            v-for="entry in shortcutEntries"
            :key="entry.path"
            type="button"
            class="shortcut-item"
            @click="router.push(entry.path)"
          >
            <el-icon :size="18"><component :is="entry.icon" /></el-icon>
            <div>
              <strong>{{ entry.title }}</strong>
              <span>{{ entry.desc }}</span>
            </div>
          </button>
        </div>
      </el-card>
    </section>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: 'Dashboard' })

import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getTaskList } from '@/api/task'
import { getRoleLabel } from '@/utils/format'
import { usePageRefresh } from '@/composables/pageRefresh'

const router = useRouter()
const userStore = useUserStore()

const roleLabel = computed(() => getRoleLabel(userStore.userRole))

const pendingTasks = ref(0)
const completedTasks = ref(0)
const failedTasks = ref(0)

const totalTasks = computed(() => pendingTasks.value + completedTasks.value + failedTasks.value)

const completionRate = computed(() => {
  if (totalTasks.value === 0) return '0%'
  return `${Math.round((completedTasks.value / totalTasks.value) * 100)}%`
})

const healthLabel = computed(() => {
  if (failedTasks.value > 0) return '需要关注'
  if (pendingTasks.value > 0) return '处理中'
  return totalTasks.value > 0 ? '运行正常' : '暂无任务'
})

const healthClass = computed(() => ({
  'is-danger': failedTasks.value > 0,
  'is-warning': failedTasks.value === 0 && pendingTasks.value > 0,
  'is-success': failedTasks.value === 0 && pendingTasks.value === 0 && totalTasks.value > 0,
}))

const statusDotClass = computed(() => ({
  'is-danger': failedTasks.value > 0,
  'is-warning': failedTasks.value === 0 && pendingTasks.value > 0,
  'is-success': failedTasks.value === 0 && pendingTasks.value === 0 && totalTasks.value > 0,
}))

const taskMetrics = computed(() => [
  {
    label: '待处理',
    value: pendingTasks.value,
    hint: '查看进度',
    className: 'metric-cell--warning',
    path: '/tasks',
  },
  {
    label: '失败任务',
    value: failedTasks.value,
    hint: '优先处理',
    className: 'metric-cell--danger',
    path: '/tasks',
  },
  {
    label: '已完成',
    value: completedTasks.value,
    hint: '进入报表',
    className: 'metric-cell--success',
    path: '/summary-report',
  },
])

const shortcutEntries = [
  {
    title: '上传中心',
    desc: '导入文件',
    path: '/upload',
    icon: 'Upload',
  },
  {
    title: '任务列表',
    desc: '处理进度',
    path: '/tasks',
    icon: 'List',
  },
  {
    title: '汇总报表',
    desc: '查看结果',
    path: '/summary-report',
    icon: 'DataAnalysis',
  },
]

async function fetchStats() {
  try {
    const pendingRes = await getTaskList({ page: 1, page_size: 1, status: 'queued' })
    pendingTasks.value = pendingRes.total || 0

    const completedRes = await getTaskList({ page: 1, page_size: 1, status: 'success' })
    completedTasks.value = completedRes.total || 0

    const failedRes = await getTaskList({ page: 1, page_size: 1, status: 'failed' })
    failedTasks.value = failedRes.total || 0
  } catch {
    // 首页统计不阻断工作台加载。
  }
}

onMounted(() => {
  fetchStats()
})

usePageRefresh(fetchStats)
</script>

<style scoped lang="scss">
.dashboard-page {
  max-width: none;
}

.dashboard-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 14px;
  padding: 18px 20px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-card);
  background: var(--bg-card);
  box-shadow: var(--shadow-card);
}

.summary-main {
  min-width: 0;

  h2 {
    margin: 4px 0 6px;
    color: var(--text-primary);
    font-size: 24px;
    font-weight: 700;
    line-height: 1.2;
  }
}

.summary-kicker,
.summary-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.summary-kicker {
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.summary-meta {
  color: var(--text-tertiary);
  font-size: 13px;

  span + span::before {
    content: '/';
    margin-right: 8px;
    color: var(--border-color);
  }
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: var(--text-tertiary);

  &.is-success {
    background: var(--success);
  }

  &.is-warning {
    background: var(--warning);
  }

  &.is-danger {
    background: var(--error);
  }
}

.summary-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-bottom: 14px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-card);
  background: var(--bg-card);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.metric-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 86px;
  padding: 16px 20px;
  border: 0;
  border-right: 1px solid var(--border-color-light);
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.16s;

  &:last-child {
    border-right: 0;
  }

  &:hover {
    background: var(--bg-hover);
  }

  span {
    display: block;
    margin-bottom: 6px;
    color: var(--text-tertiary);
    font-size: 13px;
  }

  strong {
    color: var(--text-primary);
    font-size: 30px;
    font-weight: 700;
    line-height: 1;
    font-variant-numeric: tabular-nums;
  }

  small {
    color: var(--text-tertiary);
    font-size: 12px;
  }

  &--warning strong {
    color: var(--warning);
  }

  &--danger strong {
    color: var(--error);
  }

  &--success strong {
    color: var(--success);
  }
}

.dashboard-board {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 14px;
}

.status-card,
.shortcut-card {
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .card-header-title {
    color: var(--text-primary);
    font-size: 15px;
    font-weight: 600;
  }
}

.status-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.status-head,
.status-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.status-head {
  span {
    color: var(--text-tertiary);
    font-size: 13px;
  }

  strong {
    color: var(--text-primary);
    font-size: 20px;
    font-weight: 700;
  }

  .is-danger {
    color: var(--error);
  }

  .is-warning {
    color: var(--warning);
  }

  .is-success {
    color: var(--success);
  }
}

.health-bar {
  height: 8px;
  border-radius: 999px;
  background: var(--border-color-light);
  overflow: hidden;

  span {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: var(--accent);
  }
}

.status-foot {
  justify-content: flex-start;
  color: var(--text-tertiary);
  font-size: 12px;
}

.shortcut-list {
  display: flex;
  flex-direction: column;
}

.shortcut-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 14px 0;
  border: 0;
  border-bottom: 1px solid var(--border-color-light);
  background: transparent;
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
  transition: color 0.16s;

  &:hover {
    color: var(--primary);
  }

  &:last-child {
    border-bottom: 0;
  }

  .el-icon {
    flex-shrink: 0;
    color: var(--primary);
  }

  div {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    width: 100%;
    min-width: 0;
  }

  strong {
    font-size: 14px;
    font-weight: 600;
  }

  span {
    color: var(--text-tertiary);
    font-size: 12px;
  }
}

@media (max-width: 1100px) {
  .dashboard-board {
    grid-template-columns: 1fr;
  }
}
</style>
