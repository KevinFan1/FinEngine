<template>
  <div class="page-container">
    <div class="dashboard-hero">
      <div class="hero-content">
        <div class="hero-kicker">
          <span class="hero-status-dot"></span>
          财务数据工作台
        </div>
        <h2>工作台</h2>
        <p>
          欢迎回来，{{ userStore.displayName }}
          <span v-if="userStore.userInfo?.org_name"> · {{ userStore.userInfo.org_name }}</span>
          <span> · {{ roleLabel }}</span>
        </p>
      </div>

      <div class="hero-status-card">
        <span class="status-label">任务健康度</span>
        <strong :class="healthClass">{{ healthLabel }}</strong>
        <div class="health-bar">
          <span :style="{ width: completionRate }"></span>
        </div>
        <p>{{ pendingTasks }} 个待处理 · {{ failedTasks }} 个失败任务</p>
      </div>

      <div class="dashboard-actions">
        <el-button type="primary" @click="router.push('/upload')">
          <el-icon><Upload /></el-icon> 上传文件
        </el-button>
        <el-button @click="router.push('/tasks')">
          <el-icon><List /></el-icon> 查看任务
        </el-button>
      </div>
    </div>

    <div class="workflow-strip">
      <div
        v-for="(step, index) in workflowSteps"
        :key="step.title"
        class="workflow-step"
        @click="router.push(step.path)"
      >
        <span class="step-index">{{ String(index + 1).padStart(2, '0') }}</span>
        <div>
          <h3>{{ step.title }}</h3>
          <p>{{ step.desc }}</p>
        </div>
      </div>
    </div>

    <div class="stats-row">
      <div
        v-for="stat in statsCards"
        :key="stat.title"
        class="stat-card"
        :class="stat.className"
        @click="router.push(stat.path)"
      >
        <div class="stat-top">
          <div class="stat-icon">
            <el-icon :size="22"><component :is="stat.icon" /></el-icon>
          </div>
          <span>{{ stat.badge }}</span>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-title">{{ stat.title }}</div>
          <div class="stat-desc">{{ stat.desc }}</div>
        </div>
      </div>
    </div>

    <div class="workbench-grid">
      <el-card shadow="never" class="section-card">
        <template #header>
          <div class="card-header">
            <span class="card-header-title">待办提醒</span>
            <el-button link type="primary" @click="router.push('/tasks')">查看全部</el-button>
          </div>
        </template>
        <div class="todo-list">
          <div v-for="item in todoItems" :key="item.title" class="todo-item">
            <div class="todo-info">
              <h4>{{ item.title }}</h4>
              <p>{{ item.desc }}</p>
            </div>
            <el-tag :type="item.type" size="small">{{ item.count }}</el-tag>
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="section-card">
        <template #header>
          <span class="card-header-title">常用操作</span>
        </template>
        <div class="entry-grid">
          <div
            v-for="entry in quickEntries"
            :key="entry.path"
            class="entry-card"
            @click="router.push(entry.path)"
          >
            <div class="entry-icon" :style="{ background: entry.iconBg }">
              <el-icon :size="24" :color="entry.iconColor"><component :is="entry.icon" /></el-icon>
            </div>
            <div class="entry-info">
              <h4>{{ entry.title }}</h4>
              <p>{{ entry.desc }}</p>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getRoleLabel } from '@/utils/format'
import { getTaskList } from '@/api/task'

const router = useRouter()
const userStore = useUserStore()

const roleLabel = computed(() => getRoleLabel(userStore.userRole))

const monthUploads = ref(0)
const pendingTasks = ref(0)
const completedTasks = ref(0)
const failedTasks = ref(0)
const summaryRecords = ref(0)

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

const statsCards = computed(() => [
  {
    title: '待处理任务',
    desc: '需要等待或继续处理',
    value: pendingTasks.value,
    icon: 'Clock',
    badge: '处理中',
    className: 'stat-card--orange',
    path: '/tasks',
  },
  {
    title: '失败任务',
    desc: '建议优先检查并重试',
    value: failedTasks.value,
    icon: 'Warning',
    badge: '优先处理',
    className: 'stat-card--purple',
    path: '/tasks',
  },
  {
    title: '已完成任务',
    desc: '当前可用于汇总查看',
    value: completedTasks.value,
    icon: 'CircleCheck',
    badge: '可汇总',
    className: 'stat-card--green',
    path: '/tasks',
  },
  {
    title: '本月上传',
    desc: '本月已上传文件数量',
    value: monthUploads.value,
    icon: 'Upload',
    badge: '本月',
    className: 'stat-card--blue',
    path: '/upload',
  },
])

const workflowSteps = [
  {
    title: '上传财务文件',
    desc: '进入上传中心，先完成文件名、平台和表头检查',
    path: '/upload',
  },
  {
    title: '跟进处理任务',
    desc: '查看解析进度，失败后进入任务列表定位原因',
    path: '/tasks',
  },
  {
    title: '查看汇总报表',
    desc: '按数据表上传年月、平台和店铺筛选，导出可交付结果',
    path: '/summary-report',
  },
]

const todoItems = computed(() => [
  {
    title: '处理中的任务',
    desc: '文件上传后会进入任务列表，可在这里跟进状态。',
    count: pendingTasks.value,
    type: 'warning',
  },
  {
    title: '失败任务',
    desc: '失败任务支持进入任务列表查看原因并手动重试。',
    count: failedTasks.value,
    type: 'danger',
  },
  {
    title: '汇总报表',
    desc: '处理完成后可进入汇总报表按上传年月、平台、店铺筛选导出。',
    count: summaryRecords.value,
    type: 'info',
  },
])

const quickEntries = [
  {
    title: '上传中心',
    desc: '快速上传财务文件，并完成格式和表头检查',
    path: '/upload',
    icon: 'Upload',
    iconBg: 'var(--primary-light)',
    iconColor: 'var(--primary)',
  },
  {
    title: '任务列表',
    desc: '查看处理进度、失败原因和手动重试',
    path: '/tasks',
    icon: 'List',
    iconBg: 'var(--warning-light)',
    iconColor: 'var(--warning)',
  },
  {
    title: '汇总报表',
    desc: '按上传年月筛选汇总，并下钻查看明细',
    path: '/summary-report',
    icon: 'DataAnalysis',
    iconBg: 'var(--info-light)',
    iconColor: 'var(--info)',
  },
  {
    title: '店铺管理',
    desc: '维护平台店铺和主体信息',
    path: '/shops',
    icon: 'Shop',
    iconBg: 'var(--success-light)',
    iconColor: 'var(--success)',
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
    // Stats are non-critical.
  }
}

onMounted(() => {
  fetchStats()
})
</script>

<style scoped lang="scss">
.page-container {
  max-width: none;
}

.dashboard-hero {
  position: relative;
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: var(--spacing);
  padding: 24px;
  overflow: hidden;
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-card);
  background:
    linear-gradient(135deg, rgba(21, 91, 213, 0.12), transparent 36%),
    linear-gradient(180deg, var(--surface-highlight), transparent),
    var(--bg-elevated);
  box-shadow: var(--shadow-card);

  &::after {
    content: '';
    position: absolute;
    right: 28%;
    top: 18px;
    width: 1px;
    height: calc(100% - 36px);
    background: var(--border-light);
  }

  .hero-content {
    position: relative;
    z-index: 1;
    flex: 1;
    min-width: 260px;

    .hero-kicker {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--primary);
      font-size: 13px;
      font-weight: 700;
      margin-bottom: 10px;
    }

    .hero-status-dot {
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--success);
      box-shadow: 0 0 0 4px var(--success-light);
    }

    h2 {
      font-size: clamp(28px, 3vw, 38px);
      font-weight: 800;
      line-height: 1.16;
      color: var(--text-primary);
      margin-bottom: 8px;
      letter-spacing: 0;
    }

    p {
      color: var(--text-secondary);
      font-size: 14px;
      line-height: 1.7;
    }
  }

  .hero-status-card {
    position: relative;
    z-index: 1;
    width: 220px;
    flex-shrink: 0;
    padding: 16px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius);
    background: var(--bg-card);
    box-shadow: var(--shadow-sm);

    .status-label {
      display: block;
      color: var(--text-tertiary);
      font-size: 12px;
      margin-bottom: 5px;
    }

    strong {
      display: block;
      color: var(--text-primary);
      font-size: 22px;
      line-height: 1.2;
      margin-bottom: 12px;

      &.is-danger {
        color: var(--error);
      }

      &.is-warning {
        color: var(--warning);
      }

      &.is-success {
        color: var(--success);
      }
    }

    .health-bar {
      height: 7px;
      border-radius: 999px;
      background: var(--border-color-light);
      overflow: hidden;
      margin-bottom: 10px;

      span {
        display: block;
        height: 100%;
        border-radius: inherit;
        background: linear-gradient(90deg, var(--primary), var(--accent));
      }
    }

    p {
      color: var(--text-tertiary);
      font-size: 12px;
      line-height: 1.5;
    }
  }

  .dashboard-actions {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: flex-start;
    gap: 8px;
    flex-wrap: wrap;
  }
}

.workflow-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--spacing);
  margin-bottom: var(--spacing);
}

.workflow-step {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  min-height: 92px;
  padding: 16px;
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-card);
  background: var(--bg-elevated);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  transition: border-color 0.16s, box-shadow 0.16s, transform 0.16s;

  &:hover {
    border-color: var(--primary-light-5);
    box-shadow: var(--shadow-card-hover);
    transform: translateY(-1px);
  }

  .step-index {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    flex-shrink: 0;
    border-radius: 50%;
    color: var(--primary);
    background: var(--primary-lighter);
    font-weight: 800;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }

  h3 {
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 5px;
  }

  p {
    color: var(--text-tertiary);
    font-size: 12px;
    line-height: 1.55;
  }
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--spacing);
  margin-bottom: var(--spacing);
}

.stat-card {
  border-radius: var(--radius);
  padding: 18px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: space-between;
  min-height: 160px;
  border: 1px solid transparent;
  box-shadow: var(--shadow-card);
  cursor: pointer;
  transition: border-color 0.16s, box-shadow 0.16s, transform 0.16s;

  &:hover {
    border-color: var(--border-color);
    box-shadow: var(--shadow-card-hover);
    transform: translateY(-1px);
  }

  .stat-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 18px;

    span {
      color: var(--text-tertiary);
      font-size: 12px;
      font-weight: 600;
    }
  }

  &--blue {
    color: var(--stat-blue-text);
    background: var(--stat-blue-bg);
    border-color: var(--stat-blue-border);
  }

  &--orange {
    color: var(--stat-orange-text);
    background: var(--stat-orange-bg);
    border-color: var(--stat-orange-border);
  }

  &--green {
    color: var(--stat-green-text);
    background: var(--stat-green-bg);
    border-color: var(--stat-green-border);
  }

  &--purple {
    color: var(--stat-coral-text);
    background: var(--stat-coral-bg);
    border-color: var(--stat-coral-border);
  }

  .stat-value {
    font-size: 34px;
    font-weight: 800;
    line-height: 1.2;
    font-variant-numeric: tabular-nums;
  }

  .stat-title {
    font-size: 13px;
    color: var(--text-secondary);
    margin-top: 4px;
  }

  .stat-desc {
    margin-top: 8px;
    font-size: 12px;
    color: var(--text-tertiary);
    line-height: 1.4;
  }

  .stat-icon {
    width: 42px;
    height: 42px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius);
    background: rgba(255, 255, 255, 0.62);
    box-shadow: var(--shadow-sm);
  }
}

.workbench-grid {
  display: grid;
  grid-template-columns: minmax(280px, 0.9fr) minmax(360px, 1.4fr);
  gap: var(--spacing);
}

.section-card {
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .card-header-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.todo-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.todo-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0 14px 14px;
  border-bottom: 1px solid var(--border-light);
  position: relative;

  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 19px;
    width: 6px;
    height: 6px;
    border-radius: 999px;
    background: var(--primary);
    box-shadow: 0 0 0 4px var(--primary-lighter);
  }

  &:last-child {
    border-bottom: none;
  }

  .todo-info {
    min-width: 0;
  }

  h4 {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 4px;
  }

  p {
    font-size: 12px;
    color: var(--text-tertiary);
    line-height: 1.5;
  }
}

.entry-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.entry-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: border-color 0.16s, background-color 0.16s, box-shadow 0.16s, transform 0.16s;
  border: 1px solid var(--border-light);
  background: var(--bg-card);
  position: relative;

  &:hover {
    background: var(--bg-hover);
    border-color: var(--primary);
    box-shadow: var(--shadow-sm);
    transform: translateY(-1px);
  }

  &::after {
    content: '';
    width: 7px;
    height: 7px;
    border-top: 1px solid var(--text-tertiary);
    border-right: 1px solid var(--text-tertiary);
    transform: rotate(45deg);
    margin-left: auto;
    flex-shrink: 0;
  }

  .entry-icon {
    width: 42px;
    height: 42px;
    border-radius: var(--radius);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .entry-info {
    flex: 1;
    min-width: 0;

    h4 {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 2px;
    }

    p {
      font-size: 12px;
      color: var(--text-tertiary);
      line-height: 1.4;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}

@media (max-width: 1100px) {
  .stats-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .workbench-grid {
    grid-template-columns: 1fr;
  }

  .dashboard-hero {
    flex-wrap: wrap;

    &::after {
      display: none;
    }
  }

  .workflow-strip {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .dashboard-hero {
    flex-direction: column;
    gap: 14px;
    padding: 18px;

    .hero-status-card {
      width: 100%;
    }
  }

  .stats-row,
  .entry-grid {
    grid-template-columns: 1fr;
  }
}
</style>
