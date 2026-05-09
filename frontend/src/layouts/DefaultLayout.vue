<template>
  <div class="layout">
    <!-- Sidebar -->
    <aside class="sidebar" :class="{ collapsed: appStore.sidebarCollapsed }">
      <div class="logo-area">
        <div class="logo-icon-wrapper">
          <svg viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg" width="24" height="24">
            <rect width="28" height="28" rx="6" fill="url(#logo-gradient)" />
            <path d="M8 10h12M8 14h8M8 18h10" stroke="#fff" stroke-width="2" stroke-linecap="round" />
            <defs>
              <linearGradient id="logo-gradient" x1="0" y1="0" x2="28" y2="28">
                <stop stop-color="#60a5fa" />
                <stop offset="1" stop-color="#2563eb" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        <transition name="fade-text">
          <div v-show="!appStore.sidebarCollapsed" class="logo-copy">
            <span class="logo-text">FinEngine</span>
            <span class="logo-subtitle">Finance OS</span>
          </div>
        </transition>
      </div>

      <el-scrollbar class="menu-scrollbar">
        <el-menu
          :default-active="activeMenu"
          :collapse="appStore.sidebarCollapsed"
          :collapse-transition="false"
          background-color="var(--sidebar-bg)"
          text-color="var(--sidebar-text)"
          active-text-color="var(--sidebar-active-text)"
          router
        >
          <el-menu-item
            v-for="item in filteredMenuItems"
            :key="item.path"
            :index="item.path"
          >
            <el-icon class="menu-icon"><component :is="item.icon" /></el-icon>
            <template #title>{{ item.title }}</template>
          </el-menu-item>
        </el-menu>
      </el-scrollbar>
    </aside>

    <!-- Main area -->
    <div class="main-area">
      <!-- Header -->
      <header class="header">
        <div class="header-left">
          <button class="collapse-btn" type="button" @click="appStore.toggleSidebar()">
            <el-icon>
            <Fold v-if="!appStore.sidebarCollapsed" />
            <Expand v-else />
            </el-icon>
          </button>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRouteTitle && currentRouteTitle !== '首页'">
              {{ currentRouteTitle }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <!-- Theme toggle button -->
          <el-tooltip :content="themeStore.mode === 'light' ? '切换暗黑模式' : '切换明亮模式'" placement="bottom">
            <button class="theme-toggle" type="button" @click="themeStore.toggleTheme()">
              <el-icon>
                <Moon v-if="themeStore.mode === 'light'" />
                <Sunny v-else />
              </el-icon>
              <span>{{ themeStore.mode === 'light' ? '暗黑' : '明亮' }}</span>
            </button>
          </el-tooltip>

          <!-- User dropdown -->
          <el-dropdown trigger="click" @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="28" style="background: var(--primary); flex-shrink: 0;">
                {{ avatarLetter }}
              </el-avatar>
              <span class="username">{{ userStore.displayName }}</span>
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>个人信息
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- Tab Bar -->
      <div class="tab-bar">
        <div
          v-for="tab in appStore.visitedTabs"
          :key="tab.path"
          class="tab-item"
          :class="{ active: tab.path === route.path }"
          @click="router.push(tab.path)"
        >
          <span>{{ tab.title }}</span>
          <el-icon
            v-if="tab.closable"
            class="tab-close"
            @click.stop="closeTab(tab)"
          >
            <Close />
          </el-icon>
        </div>
      </div>

      <!-- Content -->
      <main class="content">
        <router-view v-slot="{ Component }">
          <component :is="Component" />
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  DataAnalysis,
  Document,
  House,
  List,
  OfficeBuilding,
  Shop,
  Upload,
  User,
} from '@element-plus/icons-vue'
import { useAppStore, type Tab } from '@/stores/app'
import { useUserStore } from '@/stores/user'
import { useThemeStore } from '@/stores/theme'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()
const themeStore = useThemeStore()

interface MenuItem {
  path: string
  title: string
  icon: Component
  roles?: string[]
}

const menuItems: MenuItem[] = [
  { path: '/dashboard', title: '首页', icon: House },
  { path: '/organizations', title: '组织管理', icon: OfficeBuilding, roles: ['superadmin'] },
  { path: '/users', title: '用户管理', icon: User, roles: ['superadmin', 'org_admin'] },
  { path: '/shops', title: '店铺管理', icon: Shop },
  { path: '/upload', title: '上传中心', icon: Upload },
  { path: '/tasks', title: '任务列表', icon: List },
  { path: '/summary-report', title: '汇总报表', icon: DataAnalysis },
  { path: '/audit-logs', title: '操作日志', icon: Document, roles: ['superadmin', 'org_admin'] },
]

const filteredMenuItems = computed(() => {
  const userRole = userStore.userRole
  return menuItems.filter((item) => {
    if (!item.roles) return true
    return item.roles.includes(userRole)
  })
})

const activeMenu = computed(() => route.path)

const currentRouteTitle = computed(() => route.meta.title as string || '')

const avatarLetter = computed(() => {
  const name = userStore.userInfo?.display_name || userStore.userInfo?.username || 'U'
  return name[0].toUpperCase()
})

// Auto-add tab when route changes
watch(
  () => route.path,
  (path) => {
    const title = route.meta.title as string
    if (title && path !== '/login') {
      appStore.addTab({
        path,
        title,
        closable: path !== '/dashboard',
      })
    }
  },
  { immediate: true }
)

function closeTab(tab: Tab) {
  appStore.removeTab(tab.path)
  // If closing current tab, navigate to last remaining tab
  if (tab.path === route.path) {
    const tabs = appStore.visitedTabs
    const lastTab = tabs[tabs.length - 1]
    if (lastTab) {
      router.push(lastTab.path)
    } else {
      router.push('/dashboard')
    }
  }
}

function handleCommand(command: string) {
  if (command === 'logout') {
    userStore.logout()
  } else if (command === 'profile') {
    ElMessage.info('个人信息功能开发中')
  }
}
</script>

<style scoped lang="scss">
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--page-bg-gradient);
}

// ==============================
// Sidebar
// ==============================
.sidebar {
  width: var(--sidebar-width);
  background:
    radial-gradient(circle at 24px 18px, rgba(96, 165, 250, 0.2), transparent 28px),
    linear-gradient(180deg, rgba(255, 255, 255, 0.03), transparent 160px),
    var(--sidebar-bg);
  display: flex;
  flex-direction: column;
  transition: width 0.18s ease;
  flex-shrink: 0;
  overflow: hidden;
  border-right: 1px solid var(--sidebar-border);

  &.collapsed {
    width: var(--sidebar-collapsed-width);
  }

  .logo-area {
    height: 64px;
    display: flex;
    align-items: center;
    padding: 0 16px;
    border-bottom: 1px solid var(--sidebar-border);
    overflow: hidden;
    white-space: nowrap;
    background: rgba(255, 255, 255, 0.02);

    .logo-icon-wrapper {
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      border-radius: 10px;
      box-shadow: 0 10px 22px rgba(37, 99, 235, 0.32);
    }

    .logo-copy {
      display: grid;
      gap: 1px;
      min-width: 0;
    }

    .logo-text {
      margin-left: 10px;
      color: var(--sidebar-logo-text);
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 0;
      line-height: 1.1;
    }

    .logo-subtitle {
      margin-left: 10px;
      color: var(--sidebar-muted);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      line-height: 1.2;
    }
  }

  .menu-scrollbar {
    flex: 1;
    overflow: hidden;

    :deep(.el-scrollbar__view) {
      padding: 10px 0;
    }
  }

  .el-menu {
    border-right: none;

    :deep(.el-menu-item) {
      height: 44px;
      line-height: 44px;
      margin: 3px 10px;
      border-radius: var(--radius-btn);
      transition: background-color 0.16s, color 0.16s;
      color: var(--sidebar-text);

      &:hover {
        background: var(--sidebar-hover-bg) !important;
      }

      &.is-active {
        background: var(--sidebar-active-bg) !important;
        color: var(--sidebar-active-text) !important;
        font-weight: 500;
        position: relative;
        box-shadow: inset 0 0 0 1px rgba(96, 165, 250, 0.16);

        &::before {
          content: '';
          position: absolute;
          left: -9px;
          top: 50%;
          transform: translateY(-50%);
          width: 3px;
          height: 24px;
          background: #60a5fa;
          border-radius: 0 2px 2px 0;
        }
      }

      .el-icon {
        font-size: 18px;
      }

      .menu-icon {
        color: inherit;
        flex-shrink: 0;
      }
    }

    &.el-menu--collapse {
      :deep(.el-menu-item) {
        margin: 2px 8px;
        padding: 0 !important;

        &.is-active::before {
          display: none;
        }
      }
    }
  }
}

// ==============================
// Main Area
// ==============================
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

// ==============================
// Header
// ==============================
.header {
  height: var(--header-height);
  background: var(--header-bg);
  backdrop-filter: blur(18px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
  z-index: 10;
  box-shadow: none;
  border-bottom: 1px solid var(--header-border);

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .collapse-btn {
      width: 32px;
      height: 32px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 1px solid transparent;
      background: transparent;
      font-size: 19px;
      cursor: pointer;
      color: var(--text-secondary);
      transition: color 0.16s, background-color 0.16s, border-color 0.16s;
      padding: 0;
      border-radius: var(--radius-sm);

      &:hover {
        color: var(--primary);
        background: var(--primary-lighter);
        border-color: var(--primary-light-7);
      }
    }
  }

  .header-right {
    display: flex;
    align-items: center;

    .theme-toggle {
      height: 32px;
      padding: 0 10px;
      border: 1px solid var(--border-color);
      background: var(--bg-card);
      color: var(--text-primary);
      display: inline-flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      border-radius: var(--radius-btn);
      font-size: 13px;
      font-weight: 500;
      line-height: 1;
      box-shadow: var(--shadow-sm);
      transition: border-color 0.12s, background-color 0.12s, color 0.12s;
      margin-right: 8px;

      .el-icon {
        font-size: 16px;
      }

      &:hover {
        color: var(--primary);
        border-color: var(--primary);
        background: var(--primary-light);
      }
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: var(--radius-sm);
      transition: background-color 0.16s;

      &:hover {
        background: var(--bg-hover);
      }

      .username {
        font-size: 14px;
        color: var(--text-primary);
        max-width: 120px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }
}

// ==============================
// Tab Bar
// ==============================
.tab-bar {
  height: var(--tab-height);
  background: var(--tab-bg);
  backdrop-filter: blur(18px);
  display: flex;
  align-items: center;
  padding: 0 12px;
  gap: 4px;
  border-bottom: 1px solid var(--tab-border);
  flex-shrink: 0;
  overflow-x: auto;
  overflow-y: hidden;

  &::-webkit-scrollbar {
    height: 0;
  }

  .tab-item {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    height: 32px;
    padding: 0 14px;
    border-radius: 999px;
    font-size: 13px;
    color: var(--text-secondary);
    cursor: pointer;
    white-space: nowrap;
    transition: color 0.16s, background-color 0.16s;
    flex-shrink: 0;
    border: 1px solid transparent;

    &:hover {
      color: var(--primary);
      background: var(--primary-lighter);
    }

    &.active {
      color: var(--tab-item-active-text);
      background: var(--tab-item-active-bg);
      font-weight: 500;
      border-color: var(--border-light);
      box-shadow: var(--shadow-sm);
    }

    .tab-close {
      font-size: 12px;
      border-radius: 50%;
      transition: color 0.16s, background-color 0.16s;

      &:hover {
        background: var(--error-light);
        color: var(--error);
      }
    }
  }
}

// ==============================
// Content
// ==============================
.content {
  flex: 1;
  overflow: auto;
  background: var(--page-bg-gradient);
  padding: clamp(12px, 1.25vw, var(--spacing));
  min-width: 0;
  container-type: inline-size;
}

@media (max-width: 768px) {
  .header {
    padding: 0 12px;

    .header-left {
      gap: 10px;
      min-width: 0;
    }

    .header-right {
      flex-shrink: 0;

      .user-info {
        .username {
          display: none;
        }
      }
    }
  }

  .content {
    padding: 10px;
  }
}

.fade-text-enter-active,
.fade-text-leave-active {
  transition: opacity 0.14s;
}

.fade-text-enter-from,
.fade-text-leave-to {
  opacity: 0;
}
</style>
