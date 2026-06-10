<template>
    <div class="layout">
        <!-- Sidebar -->
        <aside
            class="sidebar"
            :class="{ collapsed: appStore.sidebarCollapsed }"
        >
            <div class="logo-area">
                <div class="logo-icon-wrapper">
                    <BrandLogo :size="30" />
                </div>
                <transition name="fade-text">
                    <div v-show="!appStore.sidebarCollapsed" class="logo-copy">
                        <span class="logo-text">FinEngine</span>
                        <span class="logo-subtitle">财务核算平台</span>
                    </div>
                </transition>
            </div>

            <el-scrollbar class="menu-scrollbar">
                <el-menu
                    :default-active="activeMenu"
                    :default-openeds="openedMenuPaths"
                    :collapse="appStore.sidebarCollapsed"
                    :collapse-transition="false"
                    background-color="var(--sidebar-bg)"
                    text-color="var(--sidebar-text)"
                    active-text-color="var(--sidebar-active-text)"
                    router
                >
                    <template
                        v-for="item in filteredMenuItems"
                        :key="item.path"
                    >
                        <div
                            v-if="item.type === 'divider'"
                            class="sidebar-menu-divider"
                            aria-hidden="true"
                        />
                        <el-sub-menu
                            v-else-if="item.children?.length"
                            :index="item.path"
                            popper-class="sidebar-sub-menu-popper"
                        >
                            <template #title>
                                <el-icon class="menu-icon"
                                    ><component :is="item.icon"
                                /></el-icon>
                                <span>{{ item.title }}</span>
                            </template>
                            <template
                                v-for="child in item.children"
                                :key="child.path"
                            >
                                <el-menu-item
                                    :index="child.path"
                                >
                                    <el-icon class="menu-icon"
                                        ><component :is="child.icon"
                                    /></el-icon>
                                    <template #title>{{
                                        child.title
                                    }}</template>
                                </el-menu-item>
                            </template>
                        </el-sub-menu>
                        <el-menu-item v-else :index="item.path">
                            <el-icon class="menu-icon"
                                ><component :is="item.icon"
                            /></el-icon>
                            <template #title>{{ item.title }}</template>
                        </el-menu-item>
                    </template>
                </el-menu>
            </el-scrollbar>

            <div class="sidebar-guide">
                <button
                    type="button"
                    class="guide-entry"
                    :class="{
                        'guide-entry--collapsed': appStore.sidebarCollapsed,
                    }"
                    @click="guideDrawerVisible = true"
                >
                    <div class="guide-entry-icon">
                        <el-icon><QuestionFilled /></el-icon>
                    </div>
                    <transition name="fade-text">
                        <div
                            v-show="!appStore.sidebarCollapsed"
                            class="guide-entry-copy"
                        >
                            <span class="guide-entry-title">系统使用指引</span>
                            <span class="guide-entry-desc"
                                >流程说明、图片示例、常见问题</span
                            >
                        </div>
                    </transition>
                </button>
            </div>
        </aside>

        <!-- Main area -->
        <div class="main-area">
            <!-- Header -->
            <header class="header">
                <div class="header-left">
                    <button
                        class="collapse-btn"
                        type="button"
                        @click="appStore.toggleSidebar()"
                    >
                        <el-icon>
                            <Fold v-if="!appStore.sidebarCollapsed" />
                            <Expand v-else />
                        </el-icon>
                    </button>
                    <el-breadcrumb separator="/">
                        <el-breadcrumb-item :to="{ path: '/dashboard' }"
                            >首页</el-breadcrumb-item
                        >
                        <el-breadcrumb-item
                            v-if="
                                currentRouteParentTitle &&
                                currentRouteParentTitle !== '工作台' &&
                                currentRouteTitle !== currentRouteParentTitle
                            "
                        >
                            {{ currentRouteParentTitle }}
                        </el-breadcrumb-item>
                        <el-breadcrumb-item
                            v-if="
                                currentRouteTitle &&
                                currentRouteTitle !== '首页'
                            "
                        >
                            {{ currentRouteTitle }}
                        </el-breadcrumb-item>
                    </el-breadcrumb>
                </div>
                <div class="header-right">
                    <QuotaWarning />

                    <el-popover
                        :visible="downloadCenterPopoverVisible"
                        placement="bottom-end"
                        trigger="click"
                        :width="520"
                        popper-class="download-center-popover"
                        @update:visible="downloadCenterPopoverVisible = $event"
                    >
                        <template #reference>
                            <button
                                class="download-center-entry"
                                :class="{ 'download-center-entry--active': hasActiveDownloadJobs }"
                                type="button"
                                :aria-label="downloadCenterTooltip"
                            >
                                <span
                                    v-if="hasActiveDownloadJobs"
                                    class="download-center-pulse"
                                    aria-hidden="true"
                                ></span>
                                <el-icon><Download /></el-icon>
                                <span
                                    v-if="activeDownloadJobCount > 0"
                                    class="download-center-count"
                                >
                                    {{ activeDownloadJobCount }}
                                </span>
                            </button>
                        </template>

                        <div class="download-center-panel">
                            <div class="download-center-panel__header">
                                <div class="download-center-panel__headline">
                                    <span class="download-center-panel__eyebrow">下载中心</span>
                                    <strong>最近导出任务</strong>
                                    <p>查看最近生成结果，完成后可直接下载</p>
                                </div>
                                <span class="download-center-panel__summary">
                                    {{
                                        hasActiveDownloadJobs
                                            ? `${activeDownloadJobCount} 个任务处理中`
                                            : "全部任务已完成"
                                    }}
                                </span>
                            </div>

                            <div class="download-center-panel__body">
                                <el-scrollbar
                                    v-if="recentDownloadJobs.length"
                                    class="download-center-panel__scroll"
                                >
                                    <div class="download-center-panel__list">
                                        <div class="download-center-panel__columns" aria-hidden="true">
                                            <span class="download-center-panel__column-title">文件名称</span>
                                            <span class="download-center-panel__column-title">状态</span>
                                            <span class="download-center-panel__column-title">按钮</span>
                                        </div>
                                        <div
                                            v-for="job in recentDownloadJobs"
                                            :key="job.id"
                                            class="download-center-job"
                                        >
                                            <strong
                                                class="download-center-job__filename"
                                                :title="downloadJobFilenameLabel(job)"
                                            >
                                                {{ downloadJobFilenameLabel(job) }}
                                            </strong>
                                            <span
                                                class="download-center-job__status"
                                                :class="`is-${job.status}`"
                                                :aria-label="`状态：${downloadJobStatusLabel(job.status)}`"
                                            >
                                                <span class="download-center-job__status-dot" aria-hidden="true"></span>
                                            </span>
                                            <div class="download-center-job__action-cell">
                                                <button
                                                    v-if="job.status === 'success'"
                                                    type="button"
                                                    class="download-center-job__action"
                                                    :disabled="downloadingHeaderJobId === job.id"
                                                    @click="downloadHeaderJob(job)"
                                                >
                                                    {{
                                                        downloadingHeaderJobId === job.id
                                                            ? "下载中"
                                                            : "下载"
                                                    }}
                                                </button>
                                                <span v-else class="download-center-job__action-placeholder">-</span>
                                            </div>
                                        </div>
                                    </div>
                                </el-scrollbar>

                                <div
                                    v-else
                                    class="download-center-panel__empty"
                                >
                                    暂无导出任务
                                </div>
                            </div>

                            <div class="download-center-panel__footer">
                                <button
                                    type="button"
                                    class="download-center-panel__link"
                                    @click="openDownloadCenterEntry"
                                >
                                    <span>查看全部</span>
                                    <span class="download-center-panel__link-icon" aria-hidden="true">›</span>
                                </button>
                            </div>
                        </div>
                    </el-popover>

                    <!-- Theme toggle button -->
                    <el-tooltip
                        :content="
                            themeStore.mode === 'light'
                                ? '切换暗黑模式'
                                : '切换明亮模式'
                        "
                        placement="bottom"
                    >
                        <button
                            class="theme-toggle"
                            type="button"
                            @click="themeStore.toggleTheme()"
                        >
                            <el-icon>
                                <Moon v-if="themeStore.mode === 'light'" />
                                <Sunny v-else />
                            </el-icon>
                            <span>{{
                                themeStore.mode === "light" ? "暗黑" : "明亮"
                            }}</span>
                        </button>
                    </el-tooltip>

                    <!-- User dropdown -->
                    <el-dropdown trigger="click" @command="handleCommand">
                        <span class="user-info">
                            <el-avatar
                                :size="28"
                                style="
                                    background: var(--primary);
                                    flex-shrink: 0;
                                "
                            >
                                {{ avatarLetter }}
                            </el-avatar>
                            <span class="username">{{
                                userStore.displayName
                            }}</span>
                            <el-icon class="el-icon--right"
                                ><ArrowDown
                            /></el-icon>
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
            <div class="tab-bar" @click="hideTabContextMenu">
                <div class="tab-scroll">
                    <div
                        v-for="tab in appStore.visitedTabs"
                        :key="tab.path"
                        class="tab-item"
                        :class="{ active: tab.path === route.path }"
                        @click="openTab(tab)"
                        @contextmenu.prevent="openTabContextMenu($event, tab)"
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
                <div class="tab-cache-control">
                    <span class="tab-cache-label">保留页面状态</span>
                    <el-switch
                        :model-value="appStore.tagCacheEnabled"
                        inline-prompt
                        active-text="开"
                        inactive-text="关"
                        @change="handleTagCacheToggle"
                    />
                </div>
            </div>

            <div
                v-if="tabContextMenu.visible"
                class="tab-context-menu"
                :style="{
                    left: `${tabContextMenu.x}px`,
                    top: `${tabContextMenu.y}px`,
                }"
                @click.stop
            >
                <button
                    type="button"
                    class="tab-context-menu__item"
                    @click="refreshContextTab"
                >
                    <el-icon><Refresh /></el-icon>
                    刷新
                </button>
                <button
                    type="button"
                    class="tab-context-menu__item"
                    :disabled="!tabContextMenu.tab?.closable"
                    @click="closeContextTab"
                >
                    关闭当前
                </button>
                <button
                    type="button"
                    class="tab-context-menu__item"
                    @click="closeOtherContextTabs"
                >
                    关闭其他
                </button>
                <button
                    type="button"
                    class="tab-context-menu__item"
                    @click="closeAllContextTabs"
                >
                    关闭全部
                </button>
            </div>

            <!-- Content -->
            <main class="content" @click="hideTabContextMenu">
                <router-view v-slot="{ Component }">
                    <keep-alive :include="cachedRouteNames">
                        <component :is="Component" :key="routeViewKey" />
                    </keep-alive>
                </router-view>
            </main>
        </div>
    </div>

    <el-dialog
        v-model="guideDrawerVisible"
        title="系统使用指引"
        width="min(1280px, 96vw)"
        top="5vh"
        class="guide-dialog"
    >
        <div class="guide-dialog-body">
            <section class="guide-hero">
                <p class="guide-kicker">业务使用路径</p>
                <h3>从文件上传到报表核对，按业务目标选择入口</h3>
                <p class="guide-hero-desc">
                    这份指引面向日常核算用户，重点说明每类业务动作应该去哪里操作、
                    看什么结果、如何判断是否完成。先上传文件，再跟踪任务，
                    最后在明细、报表和下载中心完成核对与留档。
                </p>
                <div class="guide-flow">
                    <div
                        v-for="item in guideFlow"
                        :key="item.title"
                        class="guide-flow-item"
                    >
                        <span class="guide-flow-icon">{{ item.index }}</span>
                        <div>
                            <strong>{{ item.title }}</strong>
                            <p>{{ item.desc }}</p>
                        </div>
                    </div>
                </div>
            </section>

            <div class="guide-content-grid">
                <section class="guide-section">
                    <div class="guide-section-head">
                        <span class="guide-section-title">操作步骤</span>
                    </div>
                    <div class="guide-step-list">
                        <article
                            v-for="step in quickStartSteps"
                            :key="step.title"
                            class="guide-step-card"
                        >
                            <span class="guide-step-index">{{
                                step.index
                            }}</span>
                            <div class="guide-step-copy">
                                <strong>{{ step.title }}</strong>
                                <p>{{ step.desc }}</p>
                            </div>
                        </article>
                    </div>
                </section>

                <section class="guide-section">
                    <div class="guide-section-head">
                        <span class="guide-section-title">上传前检查</span>
                    </div>
                    <div class="guide-note-list">
                        <div
                            v-for="note in usageNotes"
                            :key="note.title"
                            class="guide-note-item"
                        >
                            <span class="guide-note-icon">!</span>
                            <div class="guide-note-copy">
                                <strong>{{ note.title }}</strong>
                                <p>{{ note.desc }}</p>
                            </div>
                        </div>
                    </div>
                </section>
            </div>

            <section class="guide-section">
                <div class="guide-section-head">
                    <span class="guide-section-title">功能指引表</span>
                </div>
                <div class="guide-table-wrap">
                    <table class="guide-table">
                        <thead>
                            <tr>
                                <th>业务目标</th>
                                <th>操作入口</th>
                                <th>关键动作</th>
                                <th>完成判断</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="row in guideActionRows" :key="row.goal">
                                <td>
                                    <strong>{{ row.goal }}</strong>
                                    <span>{{ row.when }}</span>
                                </td>
                                <td>{{ row.entry }}</td>
                                <td>{{ row.action }}</td>
                                <td>{{ row.outcome }}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </section>

            <section class="guide-section">
                <div class="guide-section-head">
                    <span class="guide-section-title">功能截图指引</span>
                </div>
                <div class="guide-feature-groups">
                    <section
                        v-for="group in guideFeatureGroups"
                        :key="group.title"
                        class="guide-feature-group"
                    >
                        <div class="guide-feature-group-head">
                            <div>
                                <strong>{{ group.title }}</strong>
                                <p>{{ group.desc }}</p>
                            </div>
                            <span>{{ group.items.length }} 个页面</span>
                        </div>
                        <div class="guide-screenshot-grid">
                            <figure
                                v-for="shot in group.items"
                                :key="shot.title"
                                class="guide-screenshot-card"
                            >
                                <img
                                    :src="shot.src"
                                    :alt="shot.alt"
                                    loading="lazy"
                                />
                                <figcaption>
                                    <strong>{{ shot.title }}</strong>
                                    <span>{{ shot.desc }}</span>
                                </figcaption>
                            </figure>
                        </div>
                    </section>
                </div>
            </section>

            <section class="guide-section">
                <div class="guide-section-head">
                    <span class="guide-section-title">常见问题</span>
                </div>
                <div class="guide-faq-list">
                    <details
                        v-for="faq in guideFaqs"
                        :key="faq.question"
                        class="guide-faq-item"
                    >
                        <summary>
                            <span class="guide-faq-question">
                                <span class="guide-faq-mark">Q</span>
                                <span>{{ faq.question }}</span>
                            </span>
                        </summary>
                        <div class="guide-faq-answer">
                            <span class="guide-faq-answer-mark">A</span>
                            <p>{{ faq.answer }}</p>
                        </div>
                    </details>
                </div>
            </section>
        </div>
    </el-dialog>

    <ForcePasswordChangeDialog v-model="forcePasswordVisible" />
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, provide, ref, watch, type Component } from "vue";
import { ElMessage } from "element-plus/es/components/message/index.mjs";
import { useRoute, useRouter } from "vue-router";
import {
    Collection,
    CollectionTag,
    DataAnalysis,
    Document,
    Download,
    House,
    List,
    Money,
    OfficeBuilding,
    QuestionFilled,
    Refresh,
    Setting,
    Shop,
    Upload,
    User,
    Wallet,
    Warning,
} from "@element-plus/icons-vue";
import {
    pageRefreshKey,
    type PageRefreshHandler,
    type PageRefreshRegistry,
} from "@/composables/pageRefresh";
import {
    downloadExportJobFile,
    listExportJobs,
    type ExportJob,
    type ExportJobStatus,
} from "@/api/exportJob";
import { useAppStore, type Tab } from "@/stores/app";
import { useUserStore } from "@/stores/user";
import { useThemeStore } from "@/stores/theme";
import BrandLogo from "@/components/BrandLogo.vue";
import ForcePasswordChangeDialog from "@/components/ForcePasswordChangeDialog.vue";
import QuotaWarning from "@/components/QuotaWarning.vue";
import { navigateToDownloadCenter } from "@/utils/downloadCenterNavigation";
import {
    filterSidebarMenuByRole,
    sidebarMenuItems,
    type ResolvedSidebarMenuItem,
    type SidebarMenuIconName,
    type SidebarMenuItem,
    type SidebarMenuLinkItem,
} from "@/layouts/sidebarMenu";

const route = useRoute();
const router = useRouter();
const appStore = useAppStore();
const userStore = useUserStore();
const themeStore = useThemeStore();
const guideDrawerVisible = ref(false);
const forcePasswordVisible = ref(false);
const activeDownloadJobCount = ref(0);
const recentDownloadJobs = ref<ExportJob[]>([]);
const downloadingHeaderJobId = ref<number | null>(null);
const downloadCenterPopoverVisible = ref(false);
let downloadJobPollTimer: ReturnType<typeof setInterval> | null = null;

const hasActiveDownloadJobs = computed(() => activeDownloadJobCount.value > 0);
const downloadCenterTooltip = computed(() =>
    hasActiveDownloadJobs.value
        ? `下载中心：有 ${activeDownloadJobCount.value} 个导出任务处理中`
        : "打开下载中心",
);
const routeRefreshNonce = ref(0);
const refreshingRouteName = ref<string | null>(null);
const pageRefreshHandlers = new Map<string, PageRefreshHandler>();

const pageRefreshRegistry: PageRefreshRegistry = {
    register(routeKey, handler) {
        pageRefreshHandlers.set(routeKey, handler);
    },
    unregister(routeKey, handler) {
        if (pageRefreshHandlers.get(routeKey) === handler) {
            pageRefreshHandlers.delete(routeKey);
        }
    },
    async refresh(routeKey) {
        const handler = pageRefreshHandlers.get(routeKey);
        if (!handler) return false;
        await handler();
        return true;
    },
};

provide(pageRefreshKey, pageRefreshRegistry);

const tabContextMenu = ref<{
    visible: boolean;
    x: number;
    y: number;
    tab: Tab | null;
}>({
    visible: false,
    x: 0,
    y: 0,
    tab: null,
});

const iconComponents: Record<SidebarMenuIconName, Component> = {
    Collection,
    CollectionTag,
    DataAnalysis,
    Document,
    Download,
    House,
    List,
    Money,
    OfficeBuilding,
    Setting,
    Shop,
    Upload,
    User,
    Wallet,
    Warning,
};

function resolveSidebarMenuIcons(
    items: SidebarMenuLinkItem[],
): ResolvedSidebarMenuItem[] {
    return items.map((item) => ({
        ...item,
        icon: iconComponents[item.icon],
        children: item.children
            ? resolveSidebarMenuIcons(item.children)
            : undefined,
    }));
}

function findMenuPath(
    items: ResolvedSidebarMenuItem[],
    routePath: string,
): ResolvedSidebarMenuItem[] {
    for (const item of items) {
        if (item.path === routePath) return [item];
        if (!item.children?.length) continue;

        const childPath = findMenuPath(item.children, routePath);
        if (childPath.length) return [item, ...childPath];
    }

    return [];
}

const menuItems = computed(() =>
    resolveSidebarMenuIcons(
        filterSidebarMenuByRole(sidebarMenuItems, userStore.userRole, userStore.isInternalOrg).filter(
            (item): item is SidebarMenuLinkItem => item.type !== "divider",
        ),
    ),
);

const filteredMenuItems = computed(() =>
    filterSidebarMenuByRole(sidebarMenuItems, userStore.userRole, userStore.isInternalOrg).map((item) =>
        item.type === "divider"
            ? item
            : {
                  ...item,
                  icon: iconComponents[item.icon],
                  children: item.children
                      ? resolveSidebarMenuIcons(item.children)
                      : undefined,
              },
    ),
);

const activeMenu = computed(() => route.path);

const openedMenuPaths = computed(() => {
    const path = findMenuPath(menuItems.value, route.path);
    return path.slice(0, -1).map((item) => item.path);
});

const currentRouteTitle = computed(() => (route.meta.title as string) || "");
const currentRouteParentTitle = computed(() => {
    const path = findMenuPath(menuItems.value, route.path);
    return path.length > 1 ? path[path.length - 2].title : "";
});

const cachedRouteNames = computed(() => {
    if (!appStore.tagCacheEnabled) return [];
    return appStore.visitedTabs
        .map((tab) => tab.name)
        .filter(
            (name): name is string =>
                Boolean(name) && name !== refreshingRouteName.value,
        );
});

const currentRouteName = computed(() =>
    route.name ? String(route.name) : route.path,
);

const routeViewKey = computed(
    () => `${currentRouteName.value}:${routeRefreshNonce.value}`,
);

const avatarLetter = computed(() => {
    const name =
        userStore.userInfo?.display_name || userStore.userInfo?.username || "U";
    return name[0].toUpperCase();
});

const guideFlow = [
    {
        index: "1",
        title: "准备资料",
        desc: "先确认店铺和账号权限。",
    },
    {
        index: "2",
        title: "上传处理",
        desc: "提交文件并跟踪任务。",
    },
    {
        index: "3",
        title: "核对结果",
        desc: "按链路查看明细和报表。",
    },
    {
        index: "4",
        title: "导出留档",
        desc: "下载文件并保留操作记录。",
    },
];

const quickStartSteps = [
    {
        index: "01",
        title: "检查店铺资料",
        desc: "进入核算上传中心下方的店铺管理，确认店铺名称、平台、组织归属正确。文件里的店铺名要和系统店铺名保持一致。",
    },
    {
        index: "02",
        title: "到上传中心提交文件",
        desc: "进入核算上传中心，选择文件后确认系统识别出的核算年月、文件类型和店铺；识别不准时先修正后再提交。",
    },
    {
        index: "03",
        title: "查看对应任务",
        desc: "普通动账文件看核算任务；抖音资金链路看资金任务；BIC 文件看 BIC 任务。失败任务先读错误原因，再决定重新统计或重新上传。",
    },
    {
        index: "04",
        title: "核对明细、报表和下载结果",
        desc: "汇总明细用于追溯业务归属，汇总报表用于按月份聚合，年度报表用于资金科目核对，大文件导出后到下载中心获取。",
    },
];

const guideActionRows = [
    {
        goal: "查看今日工作概览",
        when: "每天进入系统后",
        entry: "首页",
        action: "查看关键指标、近期任务、常用入口和异常提醒。",
        outcome: "明确当天需要上传、核对或处理的事项。",
    },
    {
        goal: "维护店铺基础资料",
        when: "新增店铺或店铺名称变化时",
        entry: "店铺管理",
        action: "维护平台、店铺名称、组织归属和启用状态。",
        outcome: "文件上传后能稳定识别并归属到正确店铺。",
    },
    {
        goal: "提交平台核算文件",
        when: "拿到平台导出的原始文件后",
        entry: "上传中心",
        action: "上传 Excel 或 CSV，核对系统识别出的年月、文件类型和店铺。",
        outcome: "上传批次生成，并进入对应任务处理流程。",
    },
    {
        goal: "跟踪普通动账核算",
        when: "上传普通动账、订单、GMV、运费险文件后",
        entry: "核算任务",
        action: "查看任务状态、错误原因、处理摘要，必要时重新统计。",
        outcome: "任务处理成功，失败原因已定位并处理。",
    },
    {
        goal: "核对动账明细和汇总",
        when: "需要按店铺、平台、月份对账时",
        entry: "汇总明细 / 汇总报表",
        action: "先用汇总明细追溯业务口径，再用汇总报表查看核算年月聚合结果。",
        outcome: "明细和报表金额可以互相解释，调整和导出有据可查。",
    },
    {
        goal: "核对资金科目",
        when: "处理抖音动账资金链路时",
        entry: "资金任务 / 科目明细 / 年度报表",
        action: "先看资金任务是否成功，再按科目明细和年度报表核对收支归类。",
        outcome: "资金科目金额可解释，年度汇总与业务预期一致。",
    },
    {
        goal: "核对 BIC 费用数据",
        when: "上传 BIC 源文件后",
        entry: "BIC任务 / BIC源明细 / BIC汇总",
        action: "先确认 BIC 任务成功，再核对源明细和店铺月份汇总。",
        outcome: "源数据与汇总金额一致，费用归属清晰。",
    },
    {
        goal: "导出与归档",
        when: "需要对账、归档或发送结果时",
        entry: "下载中心",
        action: "在目标页面发起导出，再到下载中心查看生成进度和下载文件。",
        outcome: "导出任务完成，文件可下载并留档。",
    },
    {
        goal: "维护组织内用户",
        when: "成员变更、账号停用或密码重置时",
        entry: "系统管理 / 用户管理",
        action: "新增或编辑组织内用户，处理启停用和密码重置。",
        outcome: "成员权限与组织职责匹配，离职或异常账号及时停用。",
    },
    {
        goal: "排查数据异常",
        when: "金额不一致、店铺不匹配或任务失败时",
        entry: "任务页 / 汇总明细 / 操作日志",
        action: "先看任务错误，再核对筛选条件、源文件和操作记录。",
        outcome: "定位到文件、筛选条件、权限范围或系统处理原因。",
    },
    {
        goal: "维护个人账号",
        when: "需要更新资料或修改密码时",
        entry: "个人中心",
        action: "维护个人信息，按要求修改登录密码。",
        outcome: "个人资料准确，账号安全状态可控。",
    },
];

const usageNotes = [
    {
        title: "确认文件属于已支持平台",
        desc: "上传前先确认文件来自系统已接入的平台和文件类型。不确定时先联系管理员确认，避免产生无法处理的任务。",
    },
    {
        title: "不要随意修改店铺名称",
        desc: "系统会根据店铺名称做识别、任务归属和汇总统计。店铺名称变化可能导致同一店铺数据被拆分。",
    },
    {
        title: "区分核算年月、业务年月和上传时间",
        desc: "文件名里的年月通常作为核算年月；业务年月是订单、动账或费用实际归属月份；上传时间只表示文件进入系统的时间。",
    },
    {
        title: "失败任务先看原因",
        desc: "任务失败时先在任务列表查看错误信息。数据或格式问题需要重新整理文件；系统异常可尝试重试。",
    },
];

const guideFeatureGroups = [
    {
        title: "工作台与基础准备",
        desc: "先了解整体状态，再维护店铺和个人资料，为上传识别打好基础。",
        items: [
            {
                title: "首页",
                desc: "查看系统概览、关键指标和常用入口。",
                src: "/ui-audit-screenshots/01-dashboard-light.png",
                alt: "首页页面示例",
            },
            {
                title: "店铺管理",
                desc: "维护平台店铺，保证文件和报表按店铺归属。",
                src: "/ui-audit-screenshots/01-shops-light.png",
                alt: "店铺管理页面示例",
            },
            {
                title: "个人中心",
                desc: "维护个人资料，修改登录密码。",
                src: "/ui-audit-screenshots/01-profile-light.png",
                alt: "个人中心页面示例",
            },
        ],
    },
    {
        title: "文件上传、任务跟踪与下载",
        desc: "完成文件提交、处理进度查看和导出文件下载，是日常工作最高频链路。",
        items: [
            {
                title: "上传中心",
                desc: "上传平台账单文件，确认年月、类型和店铺识别结果。",
                src: "/ui-audit-screenshots/01-upload-light.png",
                alt: "上传中心页面示例",
            },
            {
                title: "核算任务",
                desc: "查看普通动账任务状态、错误原因和重新统计入口。",
                src: "/ui-audit-screenshots/01-tasks-light.png",
                alt: "核算任务页面示例",
            },
            {
                title: "下载中心",
                desc: "查看导出任务进度，下载报表和明细文件。",
                src: "/ui-audit-screenshots/01-downloads-light.png",
                alt: "下载中心页面示例",
            },
        ],
    },
    {
        title: "动账核算结果",
        desc: "用于核对订单、动账、费用等普通核算链路的处理结果。",
        items: [
            {
                title: "汇总明细",
                desc: "按业务维度追溯订单、动账和费用处理结果。",
                src: "/ui-audit-screenshots/01-summaries-light.png",
                alt: "汇总明细页面示例",
            },
            {
                title: "汇总报表",
                desc: "按核算年月和店铺核对汇总金额并发起导出。",
                src: "/ui-audit-screenshots/01-summary-report-light.png",
                alt: "汇总报表页面示例",
            },
        ],
    },
    {
        title: "动账资金核算",
        desc: "用于抖音动账资金链路，重点核对科目归类、收支明细和年度汇总。",
        items: [
            {
                title: "资金任务",
                desc: "查看抖音动账资金链路的任务状态和处理摘要。",
                src: "/ui-audit-screenshots/01-transaction-tasks-light.png",
                alt: "资金任务页面示例",
            },
            {
                title: "科目明细",
                desc: "核对资金收支科目的明细归类和金额。",
                src: "/ui-audit-screenshots/01-transaction-summaries-light.png",
                alt: "科目明细页面示例",
            },
            {
                title: "年度报表",
                desc: "按年度查看资金科目汇总，支持对账和留档。",
                src: "/ui-audit-screenshots/01-transaction-summary-report-light.png",
                alt: "年度报表页面示例",
            },
        ],
    },
    {
        title: "BIC核算",
        desc: "用于 BIC 文件处理、源数据追溯和店铺月份维度汇总核对。",
        items: [
            {
                title: "BIC任务",
                desc: "查看 BIC 文件处理状态和失败原因。",
                src: "/ui-audit-screenshots/01-bic-tasks-light.png",
                alt: "BIC任务页面示例",
            },
            {
                title: "BIC源明细",
                desc: "查看 BIC 原始行数据，辅助核对源文件。",
                src: "/ui-audit-screenshots/01-bic-details-light.png",
                alt: "BIC源明细页面示例",
            },
            {
                title: "BIC汇总",
                desc: "按店铺和月份查看 BIC 汇总结果。",
                src: "/ui-audit-screenshots/01-bic-summary-light.png",
                alt: "BIC汇总页面示例",
            },
        ],
    },
    {
        title: "组织内管理与审计",
        desc: "组织管理员用于维护本组织用户，并追踪关键操作记录。",
        items: [
            {
                title: "系统管理 / 用户管理",
                desc: "维护本组织用户，处理账号启停和密码重置。",
                src: "/ui-audit-screenshots/01-users-light.png",
                alt: "用户管理页面示例",
            },
            {
                title: "操作日志",
                desc: "追踪上传、导出、用户和登录等关键操作记录。",
                src: "/ui-audit-screenshots/01-audit-logs-light.png",
                alt: "操作日志页面示例",
            },
        ],
    },
];

const guideFaqs = [
    {
        question: "上传文件后没有看到结果怎么办？",
        answer: "先到对应任务页查看状态。处理中需要等待；失败时查看错误原因；成功后再到汇总明细、汇总报表或下载中心核对结果。",
    },
    {
        question: "为什么文件识别不到店铺？",
        answer: "通常是文件名或文件内容里的店铺名称和店铺管理中的名称不一致。先确认店铺资料，再重新上传或调整文件命名。",
    },
    {
        question: "核算任务、资金任务和 BIC 任务有什么区别？",
        answer: "核算任务处理普通动账核算文件；资金任务处理抖音动账资金链路；BIC 任务处理 BIC 源文件。不同文件应到对应任务页查看进度。",
    },
    {
        question: "导出后在哪里下载？",
        answer: "大数据量导出一般会生成后台任务。导出完成后进入工作台 / 下载中心，找到对应文件并下载。",
    },
    {
        question: "为什么有些菜单看不到？",
        answer: "菜单会按账号权限和组织范围展示。日常核算用户只需要关注上传、任务、明细、报表和下载入口；如果缺少必要入口，请联系管理员确认权限范围。",
    },
];

// Auto-add tab when route changes
watch(
    () => route.path,
    (path) => {
        const title = route.meta.title as string;
        if (title && path !== "/login") {
            appStore.addTab({
                path,
                fullPath: route.fullPath,
                name: route.name ? String(route.name) : undefined,
                title,
                closable: path !== "/dashboard",
            });
        }
    },
    { immediate: true },
);

watch(
    () => userStore.userInfo?.must_change_password,
    (mustChangePassword) => {
        forcePasswordVisible.value = Boolean(mustChangePassword);
    },
    { immediate: true },
);

onMounted(() => {
    startDownloadJobPolling();
});

onUnmounted(() => {
    stopDownloadJobPolling();
});

function openTab(tab: Tab) {
    hideTabContextMenu();
    if (tab.path === route.path) return;
    router.push(tab.fullPath || tab.path);
}

function closeTab(tab: Tab) {
    appStore.removeTab(tab.path);
    // If closing current tab, navigate to last remaining tab
    if (tab.path === route.path) {
        const tabs = appStore.visitedTabs;
        const lastTab = tabs[tabs.length - 1];
        if (lastTab) {
            router.push(lastTab.fullPath || lastTab.path);
        } else {
            router.push("/dashboard");
        }
    }
}

function openTabContextMenu(event: MouseEvent, tab: Tab) {
    const menuWidth = 148;
    const menuHeight = 152;
    tabContextMenu.value = {
        visible: true,
        x: Math.min(event.clientX, window.innerWidth - menuWidth - 8),
        y: Math.min(event.clientY, window.innerHeight - menuHeight - 8),
        tab,
    };
}

function hideTabContextMenu() {
    tabContextMenu.value.visible = false;
}

function closeContextTab() {
    const tab = tabContextMenu.value.tab;
    if (!tab?.closable) return;
    closeTab(tab);
    hideTabContextMenu();
}

function closeOtherContextTabs() {
    const tab = tabContextMenu.value.tab;
    if (!tab) return;
    appStore.closeOtherTabs(tab.path);
    if (route.path !== tab.path) {
        router.push(tab.fullPath || tab.path);
    }
    hideTabContextMenu();
}

function closeAllContextTabs() {
    appStore.closeAllTabs();
    if (route.path !== "/dashboard") {
        router.push("/dashboard");
    }
    hideTabContextMenu();
}

async function refreshRouteFallback() {
    const routeName = currentRouteName.value;
    if (!routeName) return;

    refreshingRouteName.value = routeName;
    await nextTick();
    routeRefreshNonce.value += 1;
    refreshingRouteName.value = null;
    await nextTick();
}

async function refreshCurrentPage() {
    const handled = await pageRefreshRegistry.refresh(currentRouteName.value);
    if (!handled) {
        await refreshRouteFallback();
    }
}

async function refreshContextTab() {
    const tab = tabContextMenu.value.tab;
    if (!tab) return;

    hideTabContextMenu();
    if (tab.path !== route.path) {
        await router.push(tab.fullPath || tab.path);
        await nextTick();
    }
    await refreshCurrentPage();
}

function handleTagCacheToggle(value: string | number | boolean) {
    const enabled = Boolean(value);
    appStore.setTagCacheEnabled(enabled);
    ElMessage.success(enabled ? "已开启页面状态保留" : "已关闭页面状态保留");
}

function handleCommand(command: string) {
    if (command === "logout") {
        userStore.logout();
    } else if (command === "profile") {
        router.push("/profile");
    }
}

async function fetchActiveDownloadJobs() {
    try {
        const [queuedResult, runningResult, recentResult] = await Promise.all([
            listExportJobs({
                page: 1,
                page_size: 1,
                status: "queued",
            }),
            listExportJobs({
                page: 1,
                page_size: 1,
                status: "running",
            }),
            listExportJobs({
                page: 1,
                page_size: 6,
            }),
        ]);
        activeDownloadJobCount.value =
            Number(queuedResult.total || 0) + Number(runningResult.total || 0);
        recentDownloadJobs.value = recentResult.items || [];
    } catch {
        activeDownloadJobCount.value = 0;
        recentDownloadJobs.value = [];
    }
}

async function openDownloadCenterEntry() {
    downloadCenterPopoverVisible.value = false;
    await nextTick();
    await navigateToDownloadCenter(router, window.location);
}

function downloadJobStatusLabel(status: ExportJobStatus) {
    return {
        queued: "排队中",
        running: "生成中",
        success: "可下载",
        failed: "失败",
        expired: "已过期",
    }[status] || status;
}

function downloadJobFilenameLabel(job: ExportJob) {
    const filename = (job.filename || "").trim();
    if (filename) return filename;
    const title = (job.title || "").trim();
    if (title) return title;
    const exportType = (job.export_type || "").trim();
    if (exportType) return exportType;
    return "导出任务";
}

async function downloadHeaderJob(job: ExportJob) {
    if (downloadingHeaderJobId.value) return;

    downloadingHeaderJobId.value = job.id;
    try {
        await downloadExportJobFile(job.id);
        ElMessage.success("下载已开始");
    } catch {
        ElMessage.error("下载失败，请稍后重试");
    } finally {
        downloadingHeaderJobId.value = null;
    }
}

function startDownloadJobPolling() {
    stopDownloadJobPolling();
    fetchActiveDownloadJobs();
    downloadJobPollTimer = setInterval(() => {
        fetchActiveDownloadJobs();
    }, 15000);
}

function stopDownloadJobPolling() {
    if (downloadJobPollTimer) {
        clearInterval(downloadJobPollTimer);
        downloadJobPollTimer = null;
    }
}
</script>

<style scoped lang="scss">
.layout {
    display: flex;
    height: 100vh;
    overflow: hidden;
    background: var(--bg-page);
}

// ==============================
// Sidebar
// ==============================
.sidebar {
    width: var(--sidebar-width);
    background: var(--sidebar-bg);
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
        height: var(--header-height);
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 0 16px;
        border-bottom: 1px solid var(--sidebar-border);
        overflow: hidden;
        white-space: nowrap;
        background: transparent;

        .logo-icon-wrapper {
            width: 44px;
            height: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            border-radius: 14px;
            background: linear-gradient(
                180deg,
                rgba(255, 255, 255, 0.1),
                rgba(255, 255, 255, 0.03)
            );
            box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
        }

        .logo-copy {
            display: grid;
            gap: 3px;
            min-width: 0;
            flex: 1;
        }

        .logo-text {
            color: var(--sidebar-logo-text);
            font-size: 18px;
            font-weight: 700;
            letter-spacing: 0;
            line-height: 1.1;
        }

        .logo-subtitle {
            color: var(--sidebar-muted);
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.04em;
            line-height: 1;
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

        :deep(.el-sub-menu__title),
        :deep(.el-menu-item) {
            height: 40px;
            line-height: 40px;
            margin: 3px 10px;
            border-radius: var(--radius-btn);
            transition:
                background-color 0.16s,
                color 0.16s;
            color: var(--sidebar-text);

            &:hover {
                background: var(--sidebar-hover-bg) !important;
            }

            .el-icon {
                font-size: 18px;
            }

            .menu-icon {
                color: inherit;
                flex-shrink: 0;
            }
        }

        :deep(.el-sub-menu) {
            &.is-active > .el-sub-menu__title {
                color: var(--sidebar-active-text) !important;
                background: rgba(255, 255, 255, 0.08) !important;
                font-weight: 600;
            }

            .el-menu {
                background: transparent !important;
            }
        }

        :deep(.el-sub-menu .el-menu-item) {
            height: 36px;
            line-height: 36px;
            margin: 2px 10px 2px 22px;
            padding-left: 18px !important;
            font-size: 13px;
            border-radius: 9px;
        }

        .sidebar-menu-divider {
            height: 1px;
            margin: 8px 16px;
            background: var(--sidebar-border);
        }

        :deep(.el-menu-item) {
            &.is-active {
                background: var(--sidebar-active-bg) !important;
                color: var(--sidebar-active-text) !important;
                font-weight: 500;
                position: relative;
                box-shadow: none;

                &::before {
                    content: "";
                    position: absolute;
                    left: -9px;
                    top: 50%;
                    transform: translateY(-50%);
                    width: 3px;
                    height: 24px;
                    background: #ffffff;
                    border-radius: 0 2px 2px 0;
                }
            }
        }

        &.el-menu--collapse {
            :deep(.el-sub-menu__title),
            :deep(.el-menu-item) {
                margin: 2px 8px;
                padding: 0 !important;
                justify-content: center;

                &.is-active::before {
                    display: none;
                }
            }

            :deep(.el-sub-menu__title .el-sub-menu__icon-arrow) {
                display: none;
            }
        }
    }

    .sidebar-guide {
        padding: 10px;
        border-top: 1px solid var(--sidebar-border);
    }

    .guide-entry {
        width: 100%;
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.04);
        color: var(--sidebar-text);
        text-align: left;
        cursor: pointer;
        transition:
            border-color 0.16s,
            background-color 0.16s,
            transform 0.16s;

        &:hover {
            border-color: rgba(255, 255, 255, 0.16);
            background: rgba(255, 255, 255, 0.07);
            transform: translateY(-1px);
        }

        &--collapsed {
            justify-content: center;
            padding: 10px 0;
        }
    }

    .guide-entry-icon {
        width: 34px;
        height: 34px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 10px;
        background: rgba(22, 119, 255, 0.18);
        color: #ffffff;
        flex-shrink: 0;
        font-size: 16px;
    }

    .guide-entry-copy {
        min-width: 0;
        display: grid;
        gap: 3px;
    }

    .guide-entry-title {
        color: var(--sidebar-logo-text);
        font-size: 13px;
        font-weight: 700;
    }

    .guide-entry-desc {
        color: var(--sidebar-muted);
        font-size: 12px;
        line-height: 1.4;
    }
}

@keyframes download-pulse {
    0% {
        transform: scale(0.96);
        box-shadow: 0 0 0 0 rgba(230, 162, 60, 0.38);
    }
    70% {
        transform: scale(1);
        box-shadow: 0 0 0 9px rgba(230, 162, 60, 0);
    }
    100% {
        transform: scale(0.96);
        box-shadow: 0 0 0 0 rgba(230, 162, 60, 0);
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
            transition:
                color 0.16s,
                background-color 0.16s,
                border-color 0.16s;
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
        gap: 14px;
        flex-shrink: 0;

        .download-center-entry {
            position: relative;
            height: 32px;
            width: 34px;
            border: 1px solid var(--border-color);
            background: var(--bg-card);
            color: var(--text-primary);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            border-radius: var(--radius-btn);
            box-shadow: var(--shadow-sm);
            transition:
                border-color 0.12s,
                background-color 0.12s,
                color 0.12s,
                transform 0.12s;

            .el-icon {
                font-size: 16px;
            }

            &:hover {
                color: var(--primary);
                border-color: var(--primary);
                background: var(--primary-light);
                transform: translateY(-1px);
            }

            &--active {
                border-color: color-mix(in srgb, var(--warning) 62%, var(--border-color));
                background: color-mix(in srgb, var(--warning) 10%, var(--bg-card));
            }

            .download-center-count {
                position: absolute;
                top: -6px;
                right: -6px;
                min-width: 18px;
                height: 18px;
                padding: 0 4px;
                border-radius: 999px;
                background: var(--warning);
                color: #fff;
                font-size: 11px;
                font-weight: 700;
                line-height: 18px;
                text-align: center;
                box-shadow: 0 4px 10px rgba(230, 162, 60, 0.28);
            }

            .download-center-pulse {
                position: absolute;
                top: 6px;
                right: 8px;
                width: 8px;
                height: 8px;
                border-radius: 999px;
                background: var(--warning);
                box-shadow: 0 0 0 rgba(230, 162, 60, 0.5);
                animation: download-pulse 1.6s ease-out infinite;
            }
        }

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
            transition:
                border-color 0.12s,
                background-color 0.12s,
                color 0.12s;

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

:global(.download-center-popover) {
    padding: 0;
    border-radius: 14px;
    border: 1px solid color-mix(in srgb, var(--primary-light-6) 48%, var(--border-light));
    overflow: hidden;
    box-shadow: 0 24px 54px rgba(15, 23, 42, 0.16);
    backdrop-filter: blur(14px);
}

:global(.download-center-popover .download-center-panel) {
    background: var(--bg-card);
    color: var(--text-primary);
}

:global(.download-center-popover .download-center-panel__header) {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    padding: 16px 16px 13px;
    background:
        linear-gradient(135deg, color-mix(in srgb, var(--primary-light) 72%, #fff) 0%, #ffffff 72%);
    border-bottom: 1px solid color-mix(in srgb, var(--primary-light-8) 68%, var(--border-light));
}

:global(.download-center-popover .download-center-panel__header strong) {
    display: block;
    font-size: 18px;
    line-height: 1.3;
    letter-spacing: 0;
}

:global(.download-center-popover .download-center-panel__header p) {
    margin: 6px 0 0;
    font-size: 12px;
    line-height: 1.55;
    color: var(--text-secondary);
}

:global(.download-center-popover .download-center-panel__headline) {
    min-width: 0;
}

:global(.download-center-popover .download-center-panel__eyebrow) {
    display: inline-block;
    margin-bottom: 4px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0;
    color: var(--primary);
}

:global(.download-center-popover .download-center-panel__summary) {
    font-size: 12px;
    line-height: 1.5;
    color: var(--primary);
    text-align: right;
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.84);
    border: 1px solid color-mix(in srgb, var(--primary-light-7) 60%, transparent);
    backdrop-filter: blur(8px);
    white-space: nowrap;
}

:global(.download-center-popover .download-center-panel__body) {
    background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.94) 0%, color-mix(in srgb, var(--bg-page) 42%, #fff) 100%);
    padding-top: 12px;
}

:global(.download-center-popover .download-center-panel__scroll) {
    max-height: 344px;
}

:global(.download-center-popover .download-center-panel__list) {
    display: flex;
    flex-direction: column;
    gap: 7px;
    padding: 0 12px 12px;
}

:global(.download-center-popover .download-center-panel__columns),
:global(.download-center-popover .download-center-job) {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 32px 64px;
    align-items: center;
    gap: 8px;
}

:global(.download-center-popover .download-center-panel__columns) {
    padding: 0 12px 2px;
    color: var(--text-tertiary);
    font-size: 11px;
    font-weight: 700;
}

:global(.download-center-popover .download-center-panel__column-title:nth-child(2)),
:global(.download-center-popover .download-center-panel__column-title:nth-child(3)) {
    text-align: center;
}

:global(.download-center-popover .download-center-job) {
    min-height: 44px;
    padding: 8px 10px 8px 12px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid color-mix(in srgb, var(--border-light) 78%, transparent);
    box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04);
    transition:
        background-color 0.14s ease,
        transform 0.14s ease,
        box-shadow 0.14s ease,
        border-color 0.14s ease;
}

:global(.download-center-popover .download-center-job:hover) {
    background: #ffffff;
    transform: translateY(-1px);
    box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
    border-color: color-mix(in srgb, var(--primary-light-6) 48%, var(--border-light));
}

:global(.download-center-popover .download-center-job__filename) {
    min-width: 0;
    font-size: 13px;
    font-weight: 600;
    line-height: 1.35;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

:global(.download-center-popover .download-center-job__action),
:global(.download-center-popover .download-center-panel__link) {
    border: 1px solid color-mix(in srgb, var(--primary-light-6) 58%, var(--border-light));
    background: #ffffff;
    color: var(--primary);
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
    padding: 0 12px;
    height: 30px;
    line-height: 28px;
    border-radius: 8px;
    flex-shrink: 0;
    box-shadow: 0 1px 3px rgba(22, 119, 255, 0.08);
    transition:
        background-color 0.14s ease,
        border-color 0.14s ease,
        box-shadow 0.14s ease,
        transform 0.14s ease;
}

:global(.download-center-popover .download-center-job__action:hover),
:global(.download-center-popover .download-center-panel__link:hover) {
    background: color-mix(in srgb, var(--primary-light) 72%, #fff);
    border-color: color-mix(in srgb, var(--primary) 36%, var(--primary-light-6));
    box-shadow: 0 6px 14px rgba(22, 119, 255, 0.14);
    transform: translateY(-1px);
}

:global(.download-center-popover .download-center-job__action:disabled) {
    cursor: wait;
    color: var(--text-disabled);
    background: var(--bg-muted);
    border-color: var(--border-light);
    transform: none;
}

:global(.download-center-popover .download-center-job__action-cell) {
    display: flex;
    justify-content: center;
    min-width: 0;
}

:global(.download-center-popover .download-center-job__action-placeholder) {
    color: var(--text-tertiary);
    font-size: 12px;
}

:global(.download-center-popover .download-center-job__status) {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
    width: 28px;
    height: 28px;
    padding: 0;
    border-radius: 999px;
    background: transparent;
}

:global(.download-center-popover .download-center-job__status-dot) {
    width: 14px;
    height: 14px;
    border-radius: 999px;
    background: currentColor;
    box-shadow:
        0 0 0 4px color-mix(in srgb, currentColor 13%, transparent),
        inset 0 0 0 2px rgba(255, 255, 255, 0.72);
}

:global(.download-center-popover .download-center-job__status.is-running),
:global(.download-center-popover .download-center-job__status.is-queued) {
    color: var(--warning);
}

:global(.download-center-popover .download-center-job__status.is-success) {
    color: var(--success);
}

:global(.download-center-popover .download-center-job__status.is-failed),
:global(.download-center-popover .download-center-job__status.is-expired) {
    color: var(--danger);
}

:global(.download-center-popover .download-center-panel__empty) {
    margin: 0 12px 12px;
    padding: 24px 16px;
    font-size: 13px;
    color: var(--text-secondary);
    text-align: center;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.92);
    border: 1px dashed color-mix(in srgb, var(--border-light) 76%, transparent);
}

:global(.download-center-popover .download-center-panel__footer) {
    display: flex;
    justify-content: flex-end;
    padding: 10px 12px 12px;
    background: #ffffff;
    border-top: 1px solid var(--border-light);
}

:global(.download-center-popover .download-center-panel__link) {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 32px;
    padding: 0 10px 0 12px;
}

:global(.download-center-popover .download-center-panel__link-icon) {
    font-size: 16px;
    line-height: 1;
}

// ==============================
// Tab Bar
// ==============================
.tab-bar {
    height: var(--tab-height);
    background: var(--tab-bg);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 12px;
    gap: 12px;
    border-bottom: 1px solid var(--tab-border);
    flex-shrink: 0;
}

.tab-scroll {
    display: flex;
    align-items: center;
    gap: 4px;
    min-width: 0;
    flex: 1;
    overflow-x: auto;
    overflow-y: hidden;

    &::-webkit-scrollbar {
        height: 0;
    }

    .tab-item {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        height: 28px;
        padding: 0 12px;
        border-radius: var(--radius-sm);
        font-size: 13px;
        color: var(--text-secondary);
        cursor: pointer;
        white-space: nowrap;
        transition:
            color 0.16s,
            background-color 0.16s;
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
            border-color: var(--primary-light-5);
            box-shadow: none;
        }

        .tab-close {
            font-size: 12px;
            border-radius: 50%;
            transition:
                color 0.16s,
                background-color 0.16s;

            &:hover {
                background: var(--error-light);
                color: var(--error);
            }
        }
    }
}

.tab-cache-control {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
}

.tab-cache-label {
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 600;
}

.tab-context-menu {
    position: fixed;
    z-index: 2200;
    min-width: 148px;
    padding: 6px;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    background: var(--bg-elevated);
    box-shadow: var(--shadow-dropdown);
}

.tab-context-menu__item {
    width: 100%;
    height: 32px;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 10px;
    border: 0;
    border-radius: 6px;
    background: transparent;
    color: var(--text-primary);
    cursor: pointer;
    font-size: 13px;
    line-height: 1;
    text-align: left;
    transition:
        background-color 0.14s,
        color 0.14s;

    &:hover:not(:disabled) {
        color: var(--primary);
        background: var(--primary-lighter);
    }

    &:disabled {
        color: var(--text-disabled);
        cursor: not-allowed;
    }

    .el-icon {
        font-size: 14px;
        flex-shrink: 0;
    }
}

// ==============================
// Content
// ==============================
.content {
    flex: 1;
    overflow: auto;
    background: var(--bg-page);
    padding: clamp(12px, 1.25vw, var(--spacing));
    min-width: 0;
    container-type: inline-size;
}

:deep(.guide-dialog) {
    border-radius: 8px;
    background: var(--bg-page);
    overflow: hidden;
    box-shadow: 0 22px 56px rgba(15, 23, 42, 0.2);

    .el-dialog__header {
        margin-bottom: 0;
        padding: 18px 24px 14px;
        border-bottom: 1px solid var(--border-light);
        color: var(--text-primary);
        font-size: 16px;
        font-weight: 700;
        background:
            linear-gradient(90deg, rgba(22, 119, 255, 0.08), transparent 52%),
            var(--bg-card);
    }

    .el-dialog__title {
        color: var(--text-primary);
        font-size: 17px;
        font-weight: 700;
    }

    .el-dialog__headerbtn {
        top: 2px;
    }

    .el-dialog__body {
        padding: 0;
        background: var(--bg-page);
    }
}

.guide-dialog-body {
    max-height: calc(90vh - 64px);
    padding: 20px 24px 26px;
    display: grid;
    gap: 18px;
    overflow-y: auto;
}

.guide-hero {
    border: 1px solid var(--border-light);
    border-radius: 8px;
    padding: 22px;
    background:
        linear-gradient(135deg, rgba(22, 119, 255, 0.12), transparent 45%),
        linear-gradient(180deg, rgba(245, 158, 11, 0.08), transparent 70%),
        var(--bg-card);

    h3 {
        margin: 6px 0 10px;
        color: var(--text-primary);
        font-size: 24px;
        line-height: 1.35;
    }
}

.guide-kicker {
    color: var(--primary);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.04em;
}

.guide-hero-desc {
    color: var(--text-secondary);
    line-height: 1.7;
    max-width: 920px;
}

.guide-flow {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin-top: 16px;
}

.guide-flow-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    min-width: 0;
    padding: 13px;
    border: 1px solid var(--border-color-light);
    border-radius: 8px;
    background: var(--bg-card);

    strong {
        display: block;
        color: var(--text-primary);
        font-size: 14px;
        line-height: 1.35;
    }

    p {
        margin-top: 3px;
        color: var(--text-tertiary);
        font-size: 12px;
        line-height: 1.5;
    }
}

.guide-flow-icon {
    width: 28px;
    height: 28px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: var(--primary);
    color: var(--primary-contrast);
    font-size: 12px;
    font-weight: 800;
    flex-shrink: 0;
}

.guide-content-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.05fr) minmax(320px, 0.95fr);
    gap: 18px;
}

.guide-section {
    min-width: 0;
}

.guide-section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-color-light);
}

.guide-section-title {
    color: var(--text-primary);
    font-size: 15px;
    font-weight: 700;
}

.guide-step-list,
.guide-note-list,
.guide-faq-list {
    display: grid;
    gap: 10px;
}

.guide-step-card,
.guide-note-item {
    border: 1px solid var(--border-light);
    border-radius: 8px;
    background: var(--surface-highlight);
}

.guide-step-card {
    display: flex;
    gap: 12px;
    padding: 14px;
    transition:
        border-color 0.18s ease,
        background-color 0.18s ease;

    &:hover {
        border-color: var(--primary-light-5);
        background: var(--bg-card);
    }
}

.guide-step-index {
    width: 38px;
    height: 38px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    background: var(--primary-light);
    color: var(--primary);
    font-size: 13px;
    font-weight: 700;
    flex-shrink: 0;
}

.guide-step-copy {
    min-width: 0;

    strong {
        display: block;
        color: var(--text-primary);
        font-size: 14px;
        line-height: 1.4;
    }

    p {
        margin-top: 4px;
        color: var(--text-secondary);
        line-height: 1.65;
    }
}

.guide-note-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 14px;
    border-color: rgba(250, 173, 20, 0.32);
    background:
        linear-gradient(
            180deg,
            rgba(250, 173, 20, 0.12),
            rgba(250, 173, 20, 0.06)
        ),
        var(--bg-card);

    &:first-child,
    &:nth-child(2),
    &:nth-child(3) {
        border-color: rgba(255, 77, 79, 0.32);
        background:
            linear-gradient(
                180deg,
                rgba(255, 77, 79, 0.12),
                rgba(255, 77, 79, 0.06)
            ),
            var(--bg-card);
    }
}

.guide-table-wrap {
    overflow: hidden;
    border: 1px solid var(--border-light);
    border-radius: 8px;
    background: var(--bg-card);
}

.guide-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;

    th,
    td {
        padding: 13px 14px;
        border-bottom: 1px solid var(--border-color-light);
        text-align: left;
        vertical-align: top;
        line-height: 1.65;
    }

    th {
        background: var(--table-header-bg);
        color: var(--text-primary);
        font-size: 13px;
        font-weight: 700;
    }

    th:first-child {
        width: 22%;
    }

    th:nth-child(2) {
        width: 18%;
    }

    th:nth-child(3) {
        width: 31%;
    }

    tbody tr {
        transition: background-color 0.16s ease;

        &:hover {
            background: var(--bg-hover);
        }

        &:last-child td {
            border-bottom: 0;
        }
    }

    td {
        color: var(--text-secondary);
        font-size: 13px;
    }

    td:first-child {
        color: var(--text-primary);

        strong,
        span {
            display: block;
        }

        strong {
            font-size: 14px;
            line-height: 1.45;
        }

        span {
            margin-top: 3px;
            color: var(--text-tertiary);
            font-size: 12px;
            line-height: 1.5;
        }
    }
}

.guide-feature-groups {
    display: grid;
    gap: 18px;
}

.guide-feature-group {
    display: grid;
    gap: 12px;
}

.guide-feature-group-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    padding: 14px;
    border: 1px solid var(--border-light);
    border-radius: 8px;
    background:
        linear-gradient(90deg, var(--primary-lighter), transparent 62%),
        var(--bg-card);

    strong {
        display: block;
        color: var(--text-primary);
        font-size: 15px;
        line-height: 1.4;
    }

    p {
        margin-top: 4px;
        color: var(--text-secondary);
        line-height: 1.65;
    }

    > span {
        padding: 4px 8px;
        border-radius: 999px;
        background: var(--bg-card);
        color: var(--primary);
        font-size: 12px;
        font-weight: 700;
        line-height: 1.2;
        white-space: nowrap;
        border: 1px solid var(--primary-light-7);
    }
}

.guide-screenshot-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
    align-items: stretch;
}

.guide-screenshot-card {
    margin: 0;
    overflow: hidden;
    border: 1px solid var(--border-light);
    border-radius: 8px;
    background: var(--surface-highlight);
    display: flex;
    flex-direction: column;
    min-height: 0;
    transition:
        border-color 0.18s ease,
        box-shadow 0.18s ease;

    &:hover {
        border-color: var(--primary-light-5);
        box-shadow: var(--shadow-md);
    }

    img {
        display: block;
        width: 100%;
        aspect-ratio: 16 / 9;
        object-fit: cover;
        object-position: top left;
        border-bottom: 1px solid var(--border-light);
        background: var(--bg-card);
    }

    figcaption {
        display: grid;
        gap: 3px;
        min-height: 74px;
        padding: 11px 12px 12px;
        align-content: start;
        flex: 1;

        strong {
            color: var(--text-primary);
            font-size: 14px;
            line-height: 1.35;
        }

        span {
            color: var(--text-secondary);
            font-size: 12px;
            line-height: 1.5;
        }
    }
}

.guide-faq-item {
    border: 1px solid var(--border-light);
    border-radius: 8px;
    background: var(--bg-card);
    overflow: hidden;
    transition:
        border-color 0.16s ease,
        box-shadow 0.16s ease;

    &[open] {
        border-color: var(--primary-light-5);
        box-shadow: var(--shadow-sm);
    }

    summary {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        min-height: 50px;
        padding: 12px 14px;
        color: var(--text-primary);
        cursor: pointer;
        font-size: 14px;
        font-weight: 700;
        line-height: 1.45;
        list-style: none;
    }

    summary::-webkit-details-marker {
        display: none;
    }

    summary::after {
        content: "";
        width: 9px;
        height: 9px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-right: 2px solid var(--text-tertiary);
        border-bottom: 2px solid var(--text-tertiary);
        transform: rotate(45deg) translateY(-2px);
        transition:
            border-color 0.16s ease,
            transform 0.16s ease;
        flex-shrink: 0;
    }

    &[open] summary::after {
        border-color: var(--primary);
        transform: rotate(225deg) translateY(-2px);
    }
}

.guide-faq-question {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
}

.guide-faq-mark,
.guide-faq-answer-mark {
    width: 24px;
    height: 24px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 800;
    flex-shrink: 0;
}

.guide-faq-mark {
    background: var(--primary-lighter);
    color: var(--primary);
}

.guide-faq-answer {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin: 0 14px 14px;
    padding: 12px;
    border: 1px solid var(--border-color-light);
    border-radius: 8px;
    background: var(--surface-highlight);
}

.guide-faq-answer-mark {
    background: var(--success-light);
    color: var(--success);
}

.guide-faq-answer {
    p {
        margin: 0;
        color: var(--text-secondary);
        line-height: 1.75;
    }
}

.guide-note-icon {
    width: 22px;
    height: 22px;
    margin-top: 1px;
    border-radius: 50%;
    background: var(--error);
    color: #ffffff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 800;
    flex-shrink: 0;
}

.guide-note-copy {
    min-width: 0;

    strong {
        display: block;
        color: var(--text-primary);
        font-size: 14px;
        line-height: 1.45;
    }

    p {
        margin-top: 4px;
        color: var(--text-secondary);
        line-height: 1.7;
    }
}

@media (max-width: 768px) {
    .tab-bar {
        height: auto;
        align-items: flex-start;
        flex-direction: column;
        padding: 8px 12px;
    }

    .tab-scroll {
        width: 100%;
    }

    .tab-cache-control {
        width: 100%;
        justify-content: flex-end;
    }

    .header {
        padding: 0 12px;

        .header-left {
            gap: 10px;
            min-width: 0;
        }

        .header-right {
            flex-shrink: 0;

            .download-center-entry {
                width: 34px;
            }

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

    :deep(.guide-dialog) {
        width: 96vw !important;
        margin-top: 2vh !important;
    }

    .guide-dialog-body {
        padding: 14px;
        max-height: calc(96vh - 58px);
    }

    .guide-hero {
        padding: 14px;

        h3 {
            font-size: 18px;
        }
    }

    .guide-flow,
    .guide-content-grid,
    .guide-screenshot-grid {
        grid-template-columns: 1fr;
    }

    .guide-feature-group-head {
        flex-direction: column;
    }

    .guide-table-wrap {
        overflow-x: auto;
    }

    .guide-table {
        min-width: 780px;
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

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}
</style>
