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
                        <el-sub-menu
                            v-if="item.children?.length"
                            :index="item.path"
                            popper-class="sidebar-sub-menu-popper"
                        >
                            <template #title>
                                <el-icon class="menu-icon"
                                    ><component :is="item.icon"
                                /></el-icon>
                                <span>{{ item.title }}</span>
                            </template>
                            <el-menu-item
                                v-for="child in item.children"
                                :key="child.path"
                                :index="child.path"
                            >
                                <el-icon class="menu-icon"
                                    ><component :is="child.icon"
                                /></el-icon>
                                <template #title>{{ child.title }}</template>
                            </el-menu-item>
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
                            <span class="guide-entry-title">使用说明</span>
                            <span class="guide-entry-desc"
                                >上传文件 -> 任务处理 -> 查看报表</span
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
                        <component :is="Component" />
                    </keep-alive>
                </router-view>
            </main>
        </div>
    </div>

    <el-drawer
        v-model="guideDrawerVisible"
        title="FinEngine 使用说明"
        size="480px"
        class="guide-drawer"
    >
        <div class="guide-drawer-body">
            <section class="guide-hero">
                <p class="guide-kicker">推荐流程</p>
                <h3>先上传，再按模块看任务和结果</h3>
                <p class="guide-hero-desc">
                    当前账号角色：{{ currentRoleLabel }}。系统主流程以 “上传中心
                    -> 核算任务 / 资金任务 / BIC任务 -> 明细 / 报表”
                    为主，基础资料只需先配置一次，后续按月重复上传即可。
                </p>
            </section>

            <section class="guide-section">
                <div class="guide-section-head">
                    <span class="guide-section-title">上手步骤</span>
                </div>
                <div class="guide-step-list">
                    <article
                        v-for="step in quickStartSteps"
                        :key="step.title"
                        class="guide-step-card"
                    >
                        <span class="guide-step-index">{{ step.index }}</span>
                        <div class="guide-step-copy">
                            <strong>{{ step.title }}</strong>
                            <p>{{ step.desc }}</p>
                        </div>
                    </article>
                </div>
            </section>

            <section class="guide-section">
                <div class="guide-section-head">
                    <span class="guide-section-title">菜单说明</span>
                </div>
                <div class="guide-menu-list">
                    <article
                        v-for="item in visibleGuideSections"
                        :key="item.title"
                        class="guide-menu-card"
                    >
                        <div class="guide-menu-main">
                            <strong>{{ item.title }}</strong>
                            <p>{{ item.desc }}</p>
                        </div>
                        <span class="guide-menu-tip">{{ item.tip }}</span>
                    </article>
                </div>
            </section>

            <section class="guide-section">
                <div class="guide-section-head">
                    <span class="guide-section-title">重点注意</span>
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
    </el-drawer>

    <ForcePasswordChangeDialog v-model="forcePasswordVisible" />
</template>

<script setup lang="ts">
import { computed, ref, watch, type Component } from "vue";
import { ElMessage } from "element-plus/es/components/message/index.mjs";
import { useRoute, useRouter } from "vue-router";
import {
    Collection,
    DataAnalysis,
    Document,
    House,
    List,
    Money,
    OfficeBuilding,
    QuestionFilled,
    Setting,
    Shop,
    Upload,
    User,
    Wallet,
} from "@element-plus/icons-vue";
import { useAppStore, type Tab } from "@/stores/app";
import { useUserStore } from "@/stores/user";
import { useThemeStore } from "@/stores/theme";
import BrandLogo from "@/components/BrandLogo.vue";
import ForcePasswordChangeDialog from "@/components/ForcePasswordChangeDialog.vue";
import QuotaWarning from "@/components/QuotaWarning.vue";

const route = useRoute();
const router = useRouter();
const appStore = useAppStore();
const userStore = useUserStore();
const themeStore = useThemeStore();
const guideDrawerVisible = ref(false);
const forcePasswordVisible = ref(false);

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

interface MenuItem {
    path: string;
    title: string;
    icon: Component;
    roles?: string[];
    children?: MenuItem[];
}

const menuItems: MenuItem[] = [
    {
        path: "/workspace",
        title: "工作台",
        icon: House,
        children: [
            { path: "/dashboard", title: "首页", icon: House },
            { path: "/upload", title: "上传中心", icon: Upload },
        ],
    },
    {
        path: "/base-data",
        title: "基础资料",
        icon: Collection,
        children: [{ path: "/shops", title: "店铺管理", icon: Shop }],
    },
    {
        path: "/order-accounting",
        title: "动账核算",
        icon: Money,
        children: [
            { path: "/tasks", title: "核算任务", icon: List },
            { path: "/summaries", title: "核算明细", icon: Document },
            { path: "/summary-report", title: "核算报表", icon: DataAnalysis },
        ],
    },
    {
        path: "/transaction-accounting",
        title: "动账资金核算",
        icon: Wallet,
        children: [
            { path: "/transaction-tasks", title: "资金任务", icon: List },
            {
                path: "/transaction-summaries",
                title: "资金明细",
                icon: Document,
            },
            {
                path: "/transaction-summary-report",
                title: "资金报表",
                icon: DataAnalysis,
            },
        ],
    },
    {
        path: "/bic-accounting",
        title: "BIC核算",
        icon: Wallet,
        children: [
            {
                path: "/bic-tasks",
                title: "BIC任务",
                icon: List,
            },
            {
                path: "/bic-details",
                title: "BIC明细",
                icon: Document,
            },
            {
                path: "/bic-report",
                title: "BIC报表",
                icon: DataAnalysis,
            },
        ],
    },
    {
        path: "/rule-config",
        title: "规则配置",
        icon: Setting,
        children: [
            {
                path: "/category-dicts",
                title: "动账重分类字典",
                icon: Collection,
                roles: ["superadmin"],
            },
            {
                path: "/transaction-rules",
                title: "资金重分类规则",
                icon: Setting,
                roles: ["superadmin"],
            },
        ],
    },
    {
        path: "/system-management",
        title: "系统管理",
        icon: OfficeBuilding,
        children: [
            {
                path: "/organizations",
                title: "组织管理",
                icon: OfficeBuilding,
                roles: ["superadmin"],
            },
            {
                path: "/users",
                title: "用户管理",
                icon: User,
                roles: ["superadmin", "org_admin"],
            },
            {
                path: "/audit-logs",
                title: "操作日志",
                icon: Document,
                roles: ["superadmin", "org_admin"],
            },
        ],
    },
];

const filteredMenuItems = computed(() => {
    const userRole = userStore.userRole;
    return menuItems.flatMap((item) => {
        if (item.roles && !item.roles.includes(userRole)) return [];
        if (!item.children?.length) return [item];
        const children = item.children.filter((child) => {
            if (!child.roles) return true;
            return child.roles.includes(userRole);
        });
        return children.length ? [{ ...item, children }] : [];
    });
});

const activeMenu = computed(() => route.path);

const openedMenuPaths = computed(() => {
    const matched = menuItems.find((item) =>
        item.children?.some((child) => child.path === route.path),
    );
    return matched ? [matched.path] : [];
});

const currentRouteTitle = computed(() => (route.meta.title as string) || "");
const currentRouteParentTitle = computed(() => {
    const matched = menuItems.find((item) =>
        item.children?.some((child) => child.path === route.path),
    );
    return matched?.title || "";
});

const cachedRouteNames = computed(() => {
    if (!appStore.tagCacheEnabled) return [];
    return appStore.visitedTabs
        .map((tab) => tab.name)
        .filter((name): name is string => Boolean(name));
});

const avatarLetter = computed(() => {
    const name =
        userStore.userInfo?.display_name || userStore.userInfo?.username || "U";
    return name[0].toUpperCase();
});

const currentRoleLabel = computed(() => {
    const role = userStore.userRole;
    if (role === "superadmin") return "超级管理员";
    if (role === "org_admin") return "组织管理员";
    return "普通用户";
});

const quickStartSteps = [
    {
        index: "01",
        title: "先维护店铺资料",
        desc: "至少保证店铺名称和实际上传文件里的店铺名一致，后续任务和报表才能稳定归集。",
    },
    {
        index: "02",
        title: "按命名规则上传文件",
        desc: "文件名建议使用“年月_性质_店铺名”，系统会先识别年月、性质、店铺，再进入上传确认。",
    },
    {
        index: "03",
        title: "按模块查看任务结果",
        desc: "普通文件先看核算任务，抖音动账文件额外看资金任务，抖音 BIC 文件额外看 BIC 任务。失败任务先看错误原因。",
    },
    {
        index: "04",
        title: "在明细和报表里核对数据",
        desc: "明细看原始处理结果，报表看聚合结果和调整后的金额，用于最终导出。",
    },
];

const guideSections = [
    {
        title: "工作台",
        desc: "从首页和上传中心进入系统主流程，先上传，再看任务，再核对结果。",
        tip: "主流程入口",
    },
    {
        title: "基础资料",
        desc: "先维护店铺资料，上传识别、任务筛选和报表汇总都会依赖这里的店铺配置。",
        tip: "先配一次",
    },
    {
        title: "动账核算",
        desc: "核算任务负责处理共享核算文件；核算明细看原始结果；核算报表看聚合结果。",
        tip: "通用链路",
    },
    {
        title: "动账资金核算",
        desc: "重点看资金任务、明细和报表，适合处理抖音动账延伸出的资金链路。",
        tip: "资金链路",
    },
    {
        title: "BIC核算",
        desc: "BIC 文件走独立任务链路，适合单独核对 BIC 相关结果。",
        tip: "独立模块",
    },
    {
        title: "规则配置",
        desc: "管理员在这里维护动账重分类字典和资金重分类规则，普通用户只需要按规则上传和核对。",
        tip: "管理员配置",
        roles: ["superadmin"],
    },
    {
        title: "系统管理",
        desc: "组织、用户和操作日志都放在这里，避免和日常核算流程混在一起。",
        tip: "后台管理",
        roles: ["superadmin", "org_admin"],
    },
];

const visibleGuideSections = computed(() => {
    const role = userStore.userRole;
    return guideSections.filter((item) => {
        if (!item.roles) return true;
        return item.roles.includes(role);
    });
});

const usageNotes = [
    {
        title: "已接入平台与支持类型",
        desc: "这里展示的是当前系统已经支持的平台和文档类型，上传前先对照确认，不在范围内的文件不要直接上传。",
    },
    {
        title: "不要随意修改店铺名称",
        desc: "系统会根据店铺名称做识别、任务归属和汇总统计，店铺名称一旦随意改动，很容易导致同一店铺数据被拆散。",
    },
    {
        title: "注意文档名称",
        desc: "上传前请重点检查文档名称，尤其是年月、性质、店铺名。文件名不规范会直接影响识别和后续汇总结果。",
    },
    {
        title: "失败任务先看原因",
        desc: "如果任务失败，先在任务列表查看错误信息，再决定重试或重新上传，不建议重复上传同一个文件。",
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
    const menuWidth = 128;
    const menuHeight = 118;
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
    min-width: 128px;
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

:deep(.guide-drawer) {
    .el-drawer__header {
        margin-bottom: 0;
        padding: 18px 20px 14px;
        border-bottom: 1px solid var(--border-light);
        color: var(--text-primary);
        font-size: 16px;
        font-weight: 700;
    }

    .el-drawer__body {
        padding: 0;
        background: var(--bg-page);
    }
}

.guide-drawer-body {
    padding: 18px 20px 24px;
    display: grid;
    gap: 16px;
}

.guide-hero,
.guide-section {
    border: 1px solid var(--border-light);
    border-radius: 14px;
    background: var(--bg-card);
}

.guide-hero {
    padding: 18px;

    h3 {
        margin: 6px 0 10px;
        color: var(--text-primary);
        font-size: 20px;
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
}

.guide-section {
    padding: 16px;
}

.guide-section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
}

.guide-section-title {
    color: var(--text-primary);
    font-size: 15px;
    font-weight: 700;
}

.guide-step-list,
.guide-menu-list,
.guide-note-list {
    display: grid;
    gap: 10px;
}

.guide-step-card,
.guide-menu-card,
.guide-note-item {
    border: 1px solid var(--border-light);
    border-radius: 12px;
    background: var(--surface-highlight);
}

.guide-step-card {
    display: flex;
    gap: 12px;
    padding: 14px;
}

.guide-step-index {
    width: 38px;
    height: 38px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 11px;
    background: var(--primary-light);
    color: var(--primary);
    font-size: 13px;
    font-weight: 700;
    flex-shrink: 0;
}

.guide-step-copy,
.guide-menu-main {
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

.guide-menu-card {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    padding: 14px;
}

.guide-menu-tip {
    padding: 4px 8px;
    border-radius: 999px;
    background: var(--primary-lighter);
    color: var(--primary);
    font-size: 12px;
    font-weight: 600;
    line-height: 1.2;
    flex-shrink: 0;
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

    .guide-drawer-body {
        padding: 14px;
    }

    .guide-hero,
    .guide-section {
        padding: 14px;
    }

    .guide-menu-card {
        flex-direction: column;
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
