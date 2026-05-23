<template>
    <div class="page-container reclass-page">
        <el-card shadow="never" class="table-card rule-table-card">
            <template #header>
                <div class="page-toolbar">
                    <div class="title-stack">
                        <span class="page-kicker">TRANSACTION RECLASS</span>
                        <div class="title-row">
                            <h2>动账重分类</h2>
                            <span class="count-text">
                                显示 {{ visibleRuleGroups.length }} / {{ ruleGroups.length }} 个父级组
                            </span>
                        </div>
                    </div>
                    <div class="toolbar-actions">
                        <el-input
                            v-model="listSearchText"
                            clearable
                            class="group-search-input"
                            placeholder="搜索科目、重分类、平台或规则条件"
                        >
                            <template #prefix>
                                <el-icon><Search /></el-icon>
                            </template>
                        </el-input>
                        <el-button @click="loadData">
                            <el-icon><Refresh /></el-icon>
                            刷新
                        </el-button>
                    </div>
                </div>

                <div class="overview-strip">
                    <article class="overview-item">
                        <span>父级科目组</span>
                        <strong>{{ ruleGroups.length }}</strong>
                        <small>按科目与平台聚合</small>
                    </article>
                    <article class="overview-item">
                        <span>子级重分类</span>
                        <strong>{{ totalCategoryCount }}</strong>
                        <small>分类节点总数</small>
                    </article>
                    <article class="overview-item">
                        <span>规则总数</span>
                        <strong>{{ rules.length }}</strong>
                        <small>全部规则明细</small>
                    </article>
                    <article class="overview-item">
                        <span>启用规则</span>
                        <strong>{{ enabledRuleCount }}</strong>
                        <small>当前生效中</small>
                    </article>
                </div>
            </template>

            <div v-loading="loading" class="group-list-table">
                <div class="group-list-head">
                    <span>科目 / 平台</span>
                    <span>状态与范围</span>
                    <span>层级统计</span>
                    <span>规则预览</span>
                    <span>操作</span>
                </div>

                <section
                    v-for="group in visibleRuleGroups"
                    :key="group.key"
                    class="group-list-group"
                    :class="{ 'is-expanded': isGroupExpanded(group.key) }"
                >
                    <div class="group-list-parent">
                        <button
                            type="button"
                            class="group-list-parent__main"
                            @click="toggleGroupExpanded(group.key)"
                        >
                            <span class="group-list-parent__icon" aria-hidden="true">
                                <el-icon>
                                    <ArrowDown v-if="isGroupExpanded(group.key)" />
                                    <ArrowRight v-else />
                                </el-icon>
                            </span>
                            <div class="group-list-parent__copy">
                                <div class="group-list-parent__title">
                                    <strong>{{ group.subjectName }}</strong>
                                    <span>科目 #{{ group.subjectId }}</span>
                                </div>
                                <div class="group-list-parent__meta">
                                    <PlatformBadge
                                        v-if="group.platformCode"
                                        :platform="group.platformCode"
                                    />
                                    <el-tag v-else size="small" effect="plain">通用</el-tag>
                                    <span>更新于 {{ formatDateTime(group.updatedAt) }}</span>
                                </div>
                            </div>
                        </button>

                        <div class="group-list-parent__status">
                            <el-tag :type="groupStatusType(group.status)" size="small">
                                {{ groupStatusLabel(group.status) }}
                            </el-tag>
                            <span>{{ group.platformCode ? "平台专属" : "通用规则" }}</span>
                        </div>

                        <div class="group-list-parent__summary">
                            <span>{{ group.categoryItems.length }} 个重分类</span>
                            <span>{{ group.rules.length }} 条规则</span>
                        </div>

                        <div class="group-list-parent__preview">
                            <span>展开后查看该科目下的分类规则</span>
                        </div>

                        <div class="group-list-parent__actions">
                            <el-button type="primary" link @click="openGroupDetail(group)">
                                查看
                            </el-button>
                            <el-button type="primary" link @click="openGroupEditor(group)">
                                编辑
                            </el-button>
                        </div>
                    </div>

                    <transition name="group-expand">
                        <div v-show="isGroupExpanded(group.key)" class="group-list-children">
                            <div
                                v-for="category in group.categoryItems"
                                :key="category.categoryId"
                                class="group-list-child"
                            >
                                <button
                                    type="button"
                                    class="group-list-child__name"
                                    @click="openGroupDetailByCategory(group, category.categoryId)"
                                >
                                    <span class="group-list-child__branch" aria-hidden="true"></span>
                                    <div class="group-list-child__copy">
                                        <strong>{{ category.categoryName }}</strong>
                                        <span>排序 {{ category.sortOrder }}</span>
                                    </div>
                                </button>

                                <div class="group-list-child__status">
                                    <el-tag
                                        :type="groupCategoryStatusType(category.status)"
                                        size="small"
                                        effect="plain"
                                    >
                                        {{ groupCategoryStatusLabel(category.status) }}
                                    </el-tag>
                                    <span>{{ category.ruleCount }} 条规则</span>
                                </div>

                                <div class="group-list-child__meta">
                                    <span>{{ category.previewLines.length }} 条预览</span>
                                </div>

                                <div class="group-list-child__preview">
                                    <span v-for="line in category.previewLines" :key="line">
                                        {{ line }}
                                    </span>
                                </div>

                                <div class="group-list-child__actions">
                                    <el-button
                                        type="primary"
                                        link
                                        @click="openGroupDetailByCategory(group, category.categoryId)"
                                    >
                                        查看
                                    </el-button>
                                    <el-button
                                        type="primary"
                                        link
                                        @click="openGroupEditor(group, category.categoryId)"
                                    >
                                        编辑
                                    </el-button>
                                </div>
                            </div>
                        </div>
                    </transition>
                </section>

                <el-empty
                    v-if="!loading && !visibleRuleGroups.length"
                    description="暂无动账重分类"
                    :image-size="80"
                />
            </div>
        </el-card>

        <el-drawer
            v-model="drawerVisible"
            :title="drawerTitle"
            size="min(1280px, 96vw)"
            class="reclass-drawer"
            append-to-body
            destroy-on-close
            :close-on-click-modal="false"
        >
            <div v-if="selectedGroup" class="group-drawer-panel">
                <section class="group-summary-card">
                    <div class="group-summary-main">
                        <span class="detail-kicker">
                            {{ drawerMode === "edit" ? "EDIT WORKBENCH" : "VIEW WORKBENCH" }}
                        </span>
                        <h3>{{ selectedGroup.subjectName }}</h3>
                        <p class="group-summary-note">
                            科目 #{{ selectedGroup.subjectId }} · {{ selectedGroupCategoryCount }} 个重分类 ·
                            {{ selectedGroupRuleCount }} 条规则
                        </p>
                        <div class="detail-badge-row">
                            <PlatformBadge
                                v-if="selectedGroup.platformCode"
                                :platform="selectedGroup.platformCode"
                            />
                            <el-tag v-else size="small" effect="plain">通用</el-tag>
                            <el-tag :type="groupStatusType(selectedGroup.status)" size="small">
                                {{ groupStatusLabel(selectedGroup.status) }}
                            </el-tag>
                        </div>
                    </div>
                    <div class="group-summary-side">
                        <div>
                            <span>更新时间</span>
                            <strong>{{ formatDateTime(selectedGroup.updatedAt) }}</strong>
                        </div>
                        <div v-if="drawerMode === 'edit'">
                            <span>状态</span>
                            <el-radio-group v-model="groupStatusValue" size="small">
                                <el-radio-button :label="1">启用</el-radio-button>
                                <el-radio-button :label="0">停用</el-radio-button>
                            </el-radio-group>
                        </div>
                    </div>
                </section>

                <section class="detail-card category-workbench">
                    <div class="workbench-head">
                        <div class="workbench-head__copy">
                            <span class="detail-kicker">CATEGORY WORKSPACE</span>
                            <div class="detail-card-header">
                                <span>重分类规则</span>
                                <span>{{ visibleCategoryPanels.length }} 类 · {{ visibleRuleTotal }} 条</span>
                            </div>
                        </div>
                        <div class="workbench-head__tools">
                            <el-input
                                v-model="drawerSearchText"
                                clearable
                                class="drawer-search-input"
                                placeholder="搜索重分类、场景、备注或表头"
                            >
                                <template #prefix>
                                    <el-icon><Search /></el-icon>
                                </template>
                            </el-input>
                            <el-button
                                v-if="drawerMode === 'edit'"
                                class="add-keyword-btn"
                                type="primary"
                                @click="addRuleToActiveCategory"
                            >
                                <el-icon><Plus /></el-icon>
                                添加规则
                            </el-button>
                        </div>
                    </div>

                    <div v-if="visibleCategoryPanels.length" class="category-editor-layout">
                        <aside class="category-sidebar" aria-label="重分类列表">
                            <div class="category-sidebar__header">
                                <span>重分类层级</span>
                                <small>{{ visibleCategoryPanels.length }} 个节点</small>
                            </div>
                            <button
                                v-for="panel in visibleCategoryPanels"
                                :key="panel.categoryId"
                                type="button"
                                class="category-tab"
                                :class="{ 'is-active': activeCategoryPanel?.categoryId === panel.categoryId }"
                                @click="setActiveCategory(panel.categoryId)"
                            >
                                <div class="category-tab__copy">
                                    <div class="category-tab__title">
                                        <span>{{ panel.categoryName }}</span>
                                        <el-tag
                                            :type="categoryPanelStatusType(panel)"
                                            size="small"
                                            effect="plain"
                                        >
                                            {{ categoryPanelStatusLabel(panel) }}
                                        </el-tag>
                                    </div>
                                    <div class="category-tab__meta">
                                        <small>{{ categoryPanelRuleCount(panel) }} 条规则</small>
                                        <small>排序 {{ panel.sortOrder }}</small>
                                    </div>
                                </div>
                            </button>
                        </aside>

                        <section
                            v-if="activeCategoryPanel"
                            class="keyword-workspace"
                            aria-label="当前重分类规则"
                        >
                            <div class="keyword-workspace__head">
                                <div class="keyword-workspace__copy">
                                    <span>当前重分类</span>
                                    <strong>{{ activeCategoryPanel.categoryName }}</strong>
                                    <p>
                                        {{
                                            activeRuleItems.length
                                                ? `${activeRuleItems.length} 条规则，重点查看触发条件与取值方式`
                                                : "当前分类还没有规则，可以直接新增配置"
                                        }}
                                    </p>
                                </div>
                                <div class="keyword-workspace__meta">
                                    <el-tag
                                        :type="categoryPanelStatusType(activeCategoryPanel)"
                                        size="small"
                                        effect="plain"
                                    >
                                        {{ categoryPanelStatusLabel(activeCategoryPanel) }}
                                    </el-tag>
                                    <span>{{ activeRuleItems.length }} 条规则</span>
                                </div>
                            </div>

                            <div v-if="activeRuleItems.length" class="rule-card-list">
                                <article
                                    v-for="(item, index) in activeRuleItems"
                                    :key="item.key"
                                    class="rule-card"
                                    :class="`rule-card--${drawerMode}`"
                                >
                                    <div class="rule-card__head">
                                        <div class="rule-card__title">
                                            <span class="rule-card__index">规则 {{ index + 1 }}</span>
                                            <strong>{{ ruleSequenceText(item) }}</strong>
                                        </div>
                                        <div class="rule-card__badges">
                                            <el-tag size="small" effect="plain">
                                                {{ item.amountField }}
                                            </el-tag>
                                            <el-tag size="small" effect="plain">
                                                {{ resultDirectionLabel(item.resultDirection) }}
                                            </el-tag>
                                        </div>
                                    </div>

                                    <div v-if="drawerMode === 'detail'" class="rule-detail-grid">
                                        <div class="rule-detail-block">
                                            <span>出入账方向</span>
                                            <strong>{{ item.transactionDirection }}</strong>
                                        </div>
                                        <div class="rule-detail-block">
                                            <span>动账场景</span>
                                            <strong>{{ sceneConditionText(item) }}</strong>
                                        </div>
                                        <div class="rule-detail-block">
                                            <span>额外备注条件</span>
                                            <strong>{{ remarkConditionText(item) }}</strong>
                                        </div>
                                        <div class="rule-detail-block">
                                            <span>规则表头</span>
                                            <strong>{{ item.amountField }}</strong>
                                        </div>
                                        <div class="rule-detail-block">
                                            <span>取值方式</span>
                                            <strong>{{ resultDirectionLabel(item.resultDirection) }}</strong>
                                        </div>
                                    </div>

                                    <div v-else class="rule-editor-grid">
                                        <label class="rule-editor-field">
                                            <span>出入账方向</span>
                                            <el-select
                                                v-model="item.transactionDirection"
                                                placeholder="方向"
                                                style="width: 100%"
                                            >
                                                <el-option
                                                    v-for="option in transactionDirectionOptions"
                                                    :key="option.value"
                                                    :label="option.label"
                                                    :value="option.value"
                                                />
                                            </el-select>
                                        </label>

                                        <label class="rule-editor-field rule-editor-field--wide">
                                            <span>动账场景</span>
                                            <div
                                                class="condition-stack"
                                                :class="{
                                                    'condition-stack--single':
                                                        item.transactionSceneMode !== 'specific',
                                                }"
                                            >
                                                <el-select
                                                    v-model="item.transactionSceneMode"
                                                    placeholder="场景"
                                                    style="width: 100%"
                                                    @change="handleSceneModeChange(item)"
                                                >
                                                    <el-option
                                                        v-for="option in transactionSceneModeOptions"
                                                        :key="option.value"
                                                        :label="option.label"
                                                        :value="option.value"
                                                    />
                                                </el-select>
                                                <el-input
                                                    v-if="item.transactionSceneMode === 'specific'"
                                                    v-model="item.transactionSceneValue"
                                                    maxlength="200"
                                                    clearable
                                                    placeholder="输入动账场景"
                                                />
                                            </div>
                                        </label>

                                        <label class="rule-editor-field rule-editor-field--wide">
                                            <span>额外备注条件</span>
                                            <div class="remark-condition-stack">
                                                <div
                                                    class="condition-stack"
                                                    :class="{ 'condition-stack--single': item.matchType === 'none' }"
                                                >
                                                    <el-select
                                                        v-model="item.matchType"
                                                        placeholder="备注条件"
                                                        style="width: 100%"
                                                        @change="handleMatchTypeChange(item)"
                                                    >
                                                        <el-option
                                                            v-for="option in matchTypeOptions"
                                                            :key="option.value"
                                                            :label="option.label"
                                                            :value="option.value"
                                                        />
                                                    </el-select>
                                                    <el-input
                                                        v-if="item.matchType !== 'none'"
                                                        v-model="item.remarkPattern"
                                                        maxlength="1000"
                                                        clearable
                                                        :placeholder="remarkPatternPlaceholder(item.matchType)"
                                                    />
                                                </div>
                                                <el-input
                                                    v-model="item.remarkExcludePattern"
                                                    maxlength="1000"
                                                    clearable
                                                    placeholder="额外不包含内容，多个用逗号分隔"
                                                />
                                            </div>
                                        </label>

                                        <label class="rule-editor-field">
                                            <span>规则表头</span>
                                            <el-input
                                                v-model="item.amountField"
                                                maxlength="100"
                                                clearable
                                                placeholder="输入表头"
                                            />
                                        </label>

                                        <label class="rule-editor-field">
                                            <span>取值方式</span>
                                            <el-select
                                                v-model="item.resultDirection"
                                                placeholder="取值"
                                                style="width: 100%"
                                            >
                                                <el-option
                                                    v-for="option in resultDirectionSelectOptions"
                                                    :key="option.value"
                                                    :label="option.label"
                                                    :value="option.value"
                                                />
                                            </el-select>
                                        </label>

                                        <el-button
                                            class="rule-delete-btn"
                                            circle
                                            text
                                            type="danger"
                                            aria-label="删除规则"
                                            @click="removeRule(activeCategoryPanel.categoryId, item.key)"
                                        >
                                            <el-icon><Close /></el-icon>
                                        </el-button>
                                    </div>
                                </article>
                            </div>

                            <el-empty
                                v-else
                                :description="
                                    drawerMode === 'edit'
                                        ? '当前重分类还没有规则，点击添加规则开始配置'
                                        : '当前重分类暂无规则'
                                "
                                :image-size="80"
                            />
                        </section>
                    </div>

                    <el-empty
                        v-else
                        description="没有匹配的重分类或规则"
                        :image-size="80"
                    />
                </section>
            </div>

            <div v-if="drawerMode === 'edit'" class="drawer-footer">
                <el-button @click="drawerVisible = false">取消</el-button>
                <el-button type="primary" :loading="submitting" @click="handleSubmitGroup">
                    确定
                </el-button>
            </div>
        </el-drawer>
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "TransactionRules" });

import { computed, nextTick, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import {
    createTransactionRule,
    deleteTransactionRule,
    listTransactionCategories,
    listTransactionRules,
    listTransactionSubjects,
    type TransactionCategory,
    type TransactionRule,
    type TransactionSubject,
    updateTransactionRule,
} from "@/api/transactionAccounting";
import { getPlatformList, type Platform } from "@/api/platform";
import PlatformBadge from "@/components/PlatformBadge.vue";
import { usePageRefresh } from "@/composables/pageRefresh";
import { formatDateTime } from "@/utils/format";
import { getFallbackPlatforms } from "@/utils/platform";

type RuleGroupStatus = "enabled" | "disabled" | "partial";
type DrawerMode = "detail" | "edit";

interface RuleGroup {
    key: string;
    subjectId: number;
    subjectName: string;
    platformCode: string | null;
    updatedAt: string;
    status: RuleGroupStatus;
    rules: TransactionRule[];
    categoryItems: GroupCategorySummary[];
}

interface GroupCategorySummary {
    categoryId: number;
    categoryName: string;
    sortOrder: number;
    status: RuleGroupStatus;
    ruleCount: number;
    previewLines: string[];
    searchText: string;
}

type RuleSceneMode = "any" | "specific" | "blank";

interface RuleItem {
    key: number;
    ruleId?: number;
    matchType: TransactionRule["match_type"];
    remarkPattern: string;
    remarkExcludePattern: string;
    transactionDirection: string;
    transactionSceneMode: RuleSceneMode;
    transactionSceneValue: string;
    amountField: string;
    resultDirection: TransactionRule["result_direction"];
    sourceRule?: TransactionRule;
    deleted?: boolean;
}

interface CategoryPanel {
    categoryId: number;
    categoryName: string;
    sortOrder: number;
    rules: RuleItem[];
    templateRule?: TransactionRule;
}

const loading = ref(false);
const submitting = ref(false);
const subjects = ref<TransactionSubject[]>([]);
const categories = ref<TransactionCategory[]>([]);
const rules = ref<TransactionRule[]>([]);
const platforms = ref<Platform[]>(getFallbackPlatforms());
const drawerVisible = ref(false);
const drawerMode = ref<DrawerMode>("detail");
const selectedGroupKey = ref("");
const activeCategoryId = ref<number | null>(null);
const drawerSearchText = ref("");
const listSearchText = ref("");
const categoryForms = ref<CategoryPanel[]>([]);
const groupStatusValue = ref<0 | 1>(1);
const keySeed = ref(1);
const expandedGroupKeys = ref<string[]>([]);

const transactionDirectionOptions = [
    { label: "入账", value: "入账" },
    { label: "出账", value: "出账" },
];

const matchTypeOptions: Array<{
    label: string;
    value: TransactionRule["match_type"];
}> = [
    { label: "不限备注", value: "none" },
    { label: "备注等于", value: "exact" },
    { label: "备注包含", value: "contains" },
    { label: "备注不包含", value: "not_contains" },
];

const transactionSceneModeOptions: Array<{
    label: string;
    value: RuleSceneMode;
}> = [
    { label: "不限场景", value: "any" },
    { label: "指定场景", value: "specific" },
    { label: "空白场景", value: "blank" },
];

const resultDirectionSelectOptions: Array<{
    label: string;
    value: TransactionRule["result_direction"];
}> = [
    { label: "原值", value: "original" },
    { label: "取正", value: "positive" },
    { label: "取负", value: "negative" },
    { label: "按方向", value: "directional" },
];

const ruleGroups = computed<RuleGroup[]>(() => {
    const groupMap = new Map<string, RuleGroup>();

    rules.value.forEach((rule) => {
        const platformCode = rule.platform_code || null;
        const key = makeGroupKey(rule.subject_id, platformCode);
        const current = groupMap.get(key);
        if (current) {
            current.rules.push(rule);
            current.updatedAt = laterDate(current.updatedAt, rule.updated_at);
            return;
        }

        groupMap.set(key, {
            key,
            subjectId: rule.subject_id,
            subjectName: ruleSubjectName(rule),
            platformCode,
            updatedAt: rule.updated_at,
            status: "disabled",
            rules: [rule],
            categoryItems: [],
        });
    });

    return Array.from(groupMap.values())
        .map((group) => {
            const categoryItems = buildGroupCategorySummaries(group.subjectId, group.rules);
            return {
                ...group,
                status: resolveGroupStatus(group.rules),
                categoryItems,
            };
        })
        .sort(
            (a, b) =>
                subjectSortOrder(a.subjectId) - subjectSortOrder(b.subjectId) ||
                a.subjectName.localeCompare(b.subjectName, "zh-Hans-CN") ||
                platformLabel(a.platformCode).localeCompare(platformLabel(b.platformCode), "zh-Hans-CN"),
        );
});

const visibleRuleGroups = computed<RuleGroup[]>(() => {
    const query = listSearchText.value.trim().toLowerCase();
    if (!query) return ruleGroups.value;

    return ruleGroups.value
        .map((group) => {
            const groupSearchText = [
                group.subjectName,
                String(group.subjectId),
                platformLabel(group.platformCode),
                groupStatusLabel(group.status),
            ]
                .join(" ")
                .toLowerCase();
            const matchedByGroup = groupSearchText.includes(query);
            const categoryItems = matchedByGroup
                ? group.categoryItems
                : group.categoryItems.filter((item) => item.searchText.includes(query));
            return { ...group, categoryItems };
        })
        .filter((group) => group.categoryItems.length);
});

const totalCategoryCount = computed(() =>
    ruleGroups.value.reduce((total, group) => total + group.categoryItems.length, 0),
);
const enabledRuleCount = computed(() => rules.value.filter((rule) => rule.status === 1).length);
const selectedGroupRuleCount = computed(() =>
    selectedGroup.value ? selectedGroup.value.rules.length : 0,
);
const selectedGroupCategoryCount = computed(() =>
    selectedGroup.value ? selectedGroup.value.categoryItems.length : 0,
);

const selectedGroup = computed(() =>
    ruleGroups.value.find((group) => group.key === selectedGroupKey.value) || null,
);

const drawerTitle = computed(() => {
    const base = drawerMode.value === "edit" ? "编辑动账重分类" : "动账重分类详情";
    return selectedGroup.value ? `${base} · ${selectedGroup.value.subjectName}` : base;
});

const drawerCategoryPanels = computed<CategoryPanel[]>(() => {
    const group = selectedGroup.value;
    if (!group) return [];
    if (drawerMode.value === "edit") {
        return categoryForms.value;
    }
    return buildCategoryPanels(group, false);
});

const visibleCategoryPanels = computed<CategoryPanel[]>(() => {
    const query = drawerSearchText.value.trim().toLowerCase();
    const panels = drawerCategoryPanels.value
        .map((panel) => ({
            ...panel,
            rules: activeRules(panel),
        }))
        .filter((panel) => drawerMode.value === "edit" || panel.rules.length);

    if (!query) return panels;

    return panels
        .map((panel) => {
            const categoryMatched = panel.categoryName.toLowerCase().includes(query);
            const matchedRules = categoryMatched
                ? panel.rules
                : panel.rules.filter((item) => buildRuleSearchText(item).includes(query));
            return { ...panel, rules: matchedRules };
        })
        .filter((panel) => panel.rules.length || panel.categoryName.toLowerCase().includes(query));
});

const activeCategoryPanel = computed(() => {
    if (!visibleCategoryPanels.value.length) return null;
    return (
        visibleCategoryPanels.value.find((panel) => panel.categoryId === activeCategoryId.value) ||
        visibleCategoryPanels.value[0]
    );
});

const activeRuleItems = computed(() => activeCategoryPanel.value?.rules || []);
const visibleRuleTotal = computed(() =>
    visibleCategoryPanels.value.reduce((total, panel) => total + panel.rules.length, 0),
);

async function loadData() {
    loading.value = true;
    try {
        const [subjectItems, categoryItems, ruleItems, platformItems] = await Promise.all([
            listTransactionSubjects(),
            listTransactionCategories(),
            listTransactionRules(),
            fetchPlatformOptions(),
        ]);
        subjects.value = subjectItems;
        categories.value = categoryItems;
        rules.value = ruleItems;
        platforms.value = platformItems;
        expandedGroupKeys.value = Array.from(
            new Set(ruleItems.map((rule) => makeGroupKey(rule.subject_id, rule.platform_code || null))),
        );
    } finally {
        loading.value = false;
    }
}

async function fetchPlatformOptions() {
    try {
        const res = await getPlatformList();
        return res.length ? res : getFallbackPlatforms();
    } catch {
        return getFallbackPlatforms();
    }
}

function openGroupDetail(group: RuleGroup) {
    drawerMode.value = "detail";
    selectedGroupKey.value = group.key;
    drawerSearchText.value = "";
    drawerVisible.value = true;
    nextTick(() => ensureActiveCategory());
}

function openGroupDetailByCategory(group: RuleGroup, categoryId: number) {
    drawerMode.value = "detail";
    selectedGroupKey.value = group.key;
    drawerSearchText.value = "";
    activeCategoryId.value = categoryId;
    drawerVisible.value = true;
    nextTick(() => ensureActiveCategory(categoryId));
}

function openGroupEditor(group: RuleGroup, preferredCategoryId?: number) {
    drawerMode.value = "edit";
    selectedGroupKey.value = group.key;
    drawerSearchText.value = "";
    groupStatusValue.value = group.status === "disabled" ? 0 : 1;
    keySeed.value = 1;
    categoryForms.value = buildCategoryPanels(group, true);
    activeCategoryId.value = preferredCategoryId ?? null;
    drawerVisible.value = true;
    nextTick(() => ensureActiveCategory(preferredCategoryId));
}

function ensureActiveCategory(preferredCategoryId?: number | null) {
    const availableIds = visibleCategoryPanels.value.map((panel) => panel.categoryId);
    if (
        preferredCategoryId &&
        availableIds.includes(preferredCategoryId)
    ) {
        activeCategoryId.value = preferredCategoryId;
        return;
    }
    if (activeCategoryId.value && availableIds.includes(activeCategoryId.value)) {
        return;
    }
    activeCategoryId.value = availableIds[0] ?? null;
}

function setActiveCategory(categoryId: number) {
    activeCategoryId.value = categoryId;
}

function addRuleToActiveCategory() {
    const categoryId = activeCategoryPanel.value?.categoryId;
    if (!categoryId) return;
    const panel = categoryForms.value.find((item) => item.categoryId === categoryId);
    if (!panel) return;
    panel.rules.push(createRuleItem(undefined, panel.templateRule));
}

function removeRule(categoryId: number, key: number) {
    const panel = categoryForms.value.find((item) => item.categoryId === categoryId);
    if (!panel) return;
    const index = panel.rules.findIndex((item) => item.key === key);
    if (index < 0) return;
    const item = panel.rules[index];
    if (item.ruleId) {
        item.deleted = true;
    } else {
        panel.rules.splice(index, 1);
    }
}

async function handleSubmitGroup() {
    const group = selectedGroup.value;
    if (!group) return;

    const activeItems = categoryForms.value.flatMap((panel) => activeRules(panel));
    if (!activeItems.length) {
        ElMessage.warning("至少保留一个规则");
        return;
    }
    const missingRemark = activeItems.some(
        (item) => item.matchType !== "none" && !item.remarkPattern.trim(),
    );
    if (missingRemark) {
        ElMessage.warning("请填写备注信息");
        return;
    }
    const missingScene = activeItems.some(
        (item) => item.transactionSceneMode === "specific" && !item.transactionSceneValue.trim(),
    );
    if (missingScene) {
        ElMessage.warning("请填写动账场景");
        return;
    }
    const missingHeader = activeItems.some((item) => !item.amountField.trim());
    if (missingHeader) {
        ElMessage.warning("请填写规则对应的表头");
        return;
    }

    submitting.value = true;
    try {
        let nextPriority = Math.max(0, ...group.rules.map((rule) => rule.priority || 0)) + 10;
        for (const panel of categoryForms.value) {
            for (const item of panel.rules) {
                const remarkPattern = item.remarkPattern.trim();
                const remarkExcludePattern = item.remarkExcludePattern.trim();
                const transactionScene = transactionSceneValueForPayload(item);
                if (item.ruleId) {
                    if (item.deleted) {
                        await deleteTransactionRule(item.ruleId);
                        continue;
                    }

                    const source = item.sourceRule || findRule(item.ruleId);
                    if (!source) continue;
                    const sourceScene = normalizeTransactionScene(source.transaction_scene);
                    if (
                        item.matchType !== source.match_type ||
                        remarkPattern !== (source.remark_pattern || "") ||
                        remarkExcludePattern !== (source.remark_exclude_pattern || "") ||
                        item.transactionDirection !== source.transaction_direction ||
                        transactionScene !== sourceScene ||
                        item.amountField.trim() !== source.amount_field ||
                        item.resultDirection !== source.result_direction ||
                        source.category_id !== panel.categoryId ||
                        source.status !== groupStatusValue.value
                    ) {
                        await updateTransactionRule(item.ruleId, {
                            subject_id: group.subjectId,
                            category_id: panel.categoryId,
                            platform_code: group.platformCode,
                            transaction_direction: item.transactionDirection,
                            remark_field: source.remark_field || "备注",
                            direction_field: source.direction_field || "动账方向",
                            transaction_scene: transactionScene,
                            match_type: item.matchType,
                            remark_pattern: remarkPattern,
                            remark_exclude_pattern: remarkExcludePattern,
                            amount_field: item.amountField.trim(),
                            result_direction: item.resultDirection,
                            priority: source.priority,
                            status: groupStatusValue.value,
                        });
                    }
                    continue;
                }

                if (!remarkPattern && item.matchType !== "none") continue;
                const template = item.sourceRule || panel.templateRule || group.rules[0];
                await createTransactionRule({
                    subject_id: group.subjectId,
                    category_id: panel.categoryId,
                    platform_code: group.platformCode,
                    transaction_direction: item.transactionDirection,
                    remark_field: template?.remark_field || "备注",
                    direction_field: template?.direction_field || "动账方向",
                    transaction_scene: transactionScene,
                    match_type: item.matchType,
                    remark_pattern: remarkPattern,
                    remark_exclude_pattern: remarkExcludePattern,
                    amount_field: item.amountField.trim(),
                    result_direction: item.resultDirection,
                    priority: nextPriority,
                    status: groupStatusValue.value,
                });
                nextPriority += 10;
            }
        }

        ElMessage.success("动账重分类已更新");
        drawerVisible.value = false;
        await loadData();
    } finally {
        submitting.value = false;
    }
}

function buildCategoryPanels(group: RuleGroup, includeEmptyCategories: boolean): CategoryPanel[] {
    const subjectCategories = categories.value
        .filter((category) => category.subject_id === group.subjectId)
        .sort((a, b) => a.sort_order - b.sort_order || a.id - b.id);
    const rulesByCategory = new Map<number, TransactionRule[]>();
    group.rules.forEach((rule) => {
        const items = rulesByCategory.get(rule.category_id) || [];
        items.push(rule);
        rulesByCategory.set(rule.category_id, items);
    });

    return subjectCategories
        .map((category) => {
            const categoryRules = (rulesByCategory.get(category.id) || []).sort(
                (a, b) => a.priority - b.priority || a.id - b.id,
            );
            return {
                categoryId: category.id,
                categoryName: category.name,
                sortOrder: category.sort_order,
                rules: categoryRules.map((rule) => createRuleItem(rule, rule)),
                templateRule: categoryRules[0] || group.rules[0],
            };
        })
        .filter((panel) => includeEmptyCategories || panel.rules.length);
}

function buildGroupCategorySummaries(subjectId: number, groupRules: TransactionRule[]) {
    const rulesByCategory = new Map<number, TransactionRule[]>();
    groupRules.forEach((rule) => {
        const items = rulesByCategory.get(rule.category_id) || [];
        items.push(rule);
        rulesByCategory.set(rule.category_id, items);
    });

    return categories.value
        .filter((category) => category.subject_id === subjectId)
        .sort((a, b) => a.sort_order - b.sort_order || a.id - b.id)
        .map((category) => {
            const categoryRules = (rulesByCategory.get(category.id) || []).sort(
                (a, b) => a.priority - b.priority || a.id - b.id,
            );
            if (!categoryRules.length) return null;
            const previewLines = categoryRules.slice(0, 3).map(buildRulePreviewLine);
            return {
                categoryId: category.id,
                categoryName: category.name,
                sortOrder: category.sort_order,
                status: resolveGroupStatus(categoryRules),
                ruleCount: categoryRules.length,
                previewLines,
                searchText: [
                    category.name,
                    groupRules.length ? ruleSubjectName(groupRules[0]) : "",
                    previewLines.join(" "),
                    ...categoryRules.map((rule) =>
                        [
                            rule.transaction_direction,
                            formatSceneConditionFromRule(rule),
                            formatRemarkCondition(
                                rule.match_type,
                                rule.remark_pattern || "",
                                rule.remark_exclude_pattern || "",
                            ),
                            rule.amount_field,
                            resultDirectionLabel(rule.result_direction),
                        ].join(" "),
                    ),
                ]
                    .join(" ")
                    .toLowerCase(),
            };
        })
        .filter((item): item is GroupCategorySummary => Boolean(item));
}

function createRuleItem(rule?: TransactionRule, templateRule?: TransactionRule): RuleItem {
    const sceneValue = normalizeTransactionScene(rule?.transaction_scene ?? templateRule?.transaction_scene);
    const sceneMode = transactionSceneModeFromValue(sceneValue);
    return {
        key: keySeed.value++,
        ruleId: rule?.id,
        matchType: rule?.match_type || templateRule?.match_type || "none",
        remarkPattern: rule?.remark_pattern || "",
        remarkExcludePattern: rule?.remark_exclude_pattern || "",
        transactionDirection: rule?.transaction_direction || templateRule?.transaction_direction || "入账",
        transactionSceneMode: sceneMode,
        transactionSceneValue: sceneMode === "specific" ? sceneValue || "" : "",
        amountField: rule?.amount_field || templateRule?.amount_field || "动账金额",
        resultDirection: rule?.result_direction || templateRule?.result_direction || "original",
        sourceRule: rule || templateRule,
        deleted: false,
    };
}

function activeRules(panel: CategoryPanel) {
    return panel.rules.filter((item) => !item.deleted);
}

function transactionSceneModeFromValue(value?: string | null): RuleSceneMode {
    if (value === null || value === undefined) return "any";
    if (value === "") return "blank";
    return "specific";
}

function normalizeTransactionScene(value?: string | null) {
    if (value === null || value === undefined) return null;
    return value;
}

function transactionSceneValueForPayload(item: RuleItem) {
    if (item.transactionSceneMode === "any") return null;
    if (item.transactionSceneMode === "blank") return "";
    return item.transactionSceneValue.trim();
}

function formatRemarkCondition(
    matchType: TransactionRule["match_type"],
    remarkPattern: string,
    remarkExcludePattern: string,
) {
    const excludeText = remarkExcludePattern.trim()
        ? `额外不包含：${remarkExcludePattern.trim()}`
        : "";
    let baseText = "不限备注";
    switch (matchType) {
        case "exact":
            baseText = `备注等于：${remarkPattern || "未填写"}`;
            break;
        case "contains":
            baseText = `备注包含：${remarkPattern || "未填写"}`;
            break;
        case "not_contains":
            baseText = `备注不包含：${remarkPattern || "未填写"}`;
            break;
        default:
            baseText = "不限备注";
    }
    return excludeText ? `${baseText}；${excludeText}` : baseText;
}

function remarkConditionText(item: RuleItem) {
    return formatRemarkCondition(item.matchType, item.remarkPattern, item.remarkExcludePattern);
}

function formatSceneCondition(mode: RuleSceneMode, value: string) {
    if (mode === "any") return "不限场景";
    if (mode === "blank") return "空白场景";
    return value.trim() || "未填写场景";
}

function formatSceneConditionFromRule(rule: TransactionRule) {
    const sceneValue = normalizeTransactionScene(rule.transaction_scene);
    const mode = transactionSceneModeFromValue(sceneValue);
    return formatSceneCondition(mode, mode === "specific" ? sceneValue || "" : "");
}

function sceneConditionText(item: RuleItem) {
    return formatSceneCondition(item.transactionSceneMode, item.transactionSceneValue);
}

function ruleSequenceParts(
    transactionDirection: string,
    sceneText: string,
    remarkText: string,
) {
    return [transactionDirection, sceneText, remarkText].filter((part) => part.trim());
}

function ruleSequenceText(item: RuleItem) {
    return ruleSequenceParts(
        item.transactionDirection,
        sceneConditionText(item),
        remarkConditionText(item),
    ).join(" · ");
}

function handleMatchTypeChange(item: RuleItem) {
    if (item.matchType !== "none" && !item.remarkPattern && item.sourceRule?.remark_pattern) {
        item.remarkPattern = item.sourceRule.remark_pattern;
    }
}

function remarkPatternPlaceholder(matchType: TransactionRule["match_type"]) {
    if (matchType === "contains") return "输入必须包含的备注内容，多个用逗号分隔";
    if (matchType === "not_contains") return "输入不能出现的备注内容，多个用逗号分隔";
    return "输入完整备注信息";
}

function handleSceneModeChange(item: RuleItem) {
    if (item.transactionSceneMode !== "specific") {
        item.transactionSceneValue = "";
        return;
    }
    if (!item.transactionSceneValue && item.sourceRule?.transaction_scene) {
        item.transactionSceneValue = item.sourceRule.transaction_scene;
    }
}

function buildRuleSearchText(item: RuleItem) {
    return [
        item.transactionDirection,
        sceneConditionText(item),
        remarkConditionText(item),
        item.amountField,
        resultDirectionLabel(item.resultDirection),
        item.remarkPattern,
        item.remarkExcludePattern,
        item.transactionSceneValue,
        item.matchType,
    ]
        .join(" ")
        .toLowerCase();
}

function buildRulePreviewLine(rule: TransactionRule) {
    return [
        rule.transaction_direction,
        formatSceneConditionFromRule(rule),
        formatRemarkCondition(
            rule.match_type,
            rule.remark_pattern || "",
            rule.remark_exclude_pattern || "",
        ),
        rule.amount_field,
    ].join(" · ");
}

function toggleGroupExpanded(groupKey: string) {
    if (expandedGroupKeys.value.includes(groupKey)) {
        expandedGroupKeys.value = expandedGroupKeys.value.filter((key) => key !== groupKey);
        return;
    }
    expandedGroupKeys.value = [...expandedGroupKeys.value, groupKey];
}

function isGroupExpanded(groupKey: string) {
    return expandedGroupKeys.value.includes(groupKey);
}

function categoryPanelRuleCount(panel: CategoryPanel) {
    return activeRules(panel).length;
}

function categoryPanelStatus(panel: CategoryPanel): RuleGroupStatus | "empty" {
    const ruleCount = categoryPanelRuleCount(panel);
    if (ruleCount === 0) return "empty";
    if (drawerMode.value === "edit") {
        return groupStatusValue.value === 1 ? "enabled" : "disabled";
    }
    const enabledCount = panel.rules.filter((item) => item.sourceRule?.status === 1).length;
    if (enabledCount === 0) return "disabled";
    if (enabledCount === ruleCount) return "enabled";
    return "partial";
}

function categoryPanelStatusLabel(panel: CategoryPanel) {
    const status = categoryPanelStatus(panel);
    if (status === "empty") return "待补充";
    return groupStatusLabel(status);
}

function categoryPanelStatusType(panel: CategoryPanel) {
    const status = categoryPanelStatus(panel);
    if (status === "empty") return "info";
    return groupStatusType(status);
}

function groupCategoryStatusLabel(status: RuleGroupStatus) {
    return groupStatusLabel(status);
}

function groupCategoryStatusType(status: RuleGroupStatus) {
    return groupStatusType(status);
}

function makeGroupKey(subjectId: number, platformCode?: string | null) {
    return `${subjectId}::${platformCode || "__all__"}`;
}

function resolveGroupStatus(groupRules: TransactionRule[]): RuleGroupStatus {
    const enabledCount = groupRules.filter((rule) => rule.status === 1).length;
    if (enabledCount === 0) return "disabled";
    if (enabledCount === groupRules.length) return "enabled";
    return "partial";
}

function groupStatusLabel(status: RuleGroupStatus) {
    return status === "enabled" ? "启用" : status === "disabled" ? "停用" : "部分启用";
}

function groupStatusType(status: RuleGroupStatus) {
    return status === "enabled" ? "success" : status === "disabled" ? "danger" : "warning";
}

function resultDirectionLabel(value: TransactionRule["result_direction"]) {
    return resultDirectionSelectOptions.find((item) => item.value === value)?.label || value;
}

function laterDate(left: string, right: string) {
    return new Date(right).getTime() > new Date(left).getTime() ? right : left;
}

function subjectSortOrder(subjectId: number) {
    return subjects.value.find((item) => item.id === subjectId)?.sort_order ?? 9999;
}

function ruleSubjectName(rule: TransactionRule) {
    return rule.subject_name || subjects.value.find((item) => item.id === rule.subject_id)?.name || "-";
}

function platformLabel(platformCode?: string | null) {
    if (!platformCode) return "通用";
    return platforms.value.find((platform) => platform.code === platformCode)?.name || platformCode;
}

function findRule(ruleId: number) {
    return rules.value.find((rule) => rule.id === ruleId);
}

onMounted(loadData);
usePageRefresh(loadData);
</script>

<style scoped lang="scss">
@use "./transaction.scss";

.reclass-page {
    display: grid;
    gap: 0;
}

.rule-table-card {
    border: 1px solid var(--border-light);

    :deep(.el-card__header) {
        padding: 16px 18px 18px;
        border-bottom: 1px solid var(--border-light);
        background: var(--bg-card);
    }

    :deep(.el-card__body) {
        padding: 0;
    }
}

.page-toolbar,
.title-row,
.toolbar-actions,
.detail-badge-row,
.detail-card-header,
.keyword-workspace__head,
.workbench-head,
.group-tree-card__head,
.group-tree-toggle,
.group-tree-title-line,
.group-tree-meta,
.group-child-card__head,
.group-child-card__stats,
.group-child-card__footer,
.rule-card__head,
.rule-card__badges {
    display: flex;
    align-items: center;
}

.page-toolbar {
    justify-content: space-between;
    gap: 18px;
}

.title-stack {
    display: grid;
    gap: 4px;
    min-width: 0;
}

.page-kicker,
.detail-kicker {
    color: var(--primary);
    font-family: "SF Mono", SFMono-Regular, Consolas, monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
}

.title-row {
    gap: 10px;
    min-width: 0;

    h2 {
        margin: 0;
        color: var(--text-primary);
        font-size: 20px;
        font-weight: 700;
        line-height: 1.3;
    }
}

.count-text {
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 500;
    white-space: nowrap;
}

.toolbar-actions,
.detail-badge-row,
.group-tree-actions,
.workbench-head__tools,
.group-list-parent__status,
.group-list-parent__summary,
.group-list-parent__actions,
.group-list-child__status,
.group-list-child__meta,
.group-list-child__actions,
.group-list-parent__title,
.group-list-parent__meta {
    flex-wrap: wrap;
    gap: 8px;
}

.group-search-input {
    width: min(360px, 44vw);
}

.group-search-input :deep(.el-input__wrapper),
.drawer-search-input :deep(.el-input__wrapper) {
    background: var(--bg-elevated);
}

.overview-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin-top: 14px;
}

.overview-card {
    display: grid;
    gap: 6px;
    min-width: 0;
    padding: 12px 14px;
    border: 1px solid var(--border-color-light);
    border-radius: 10px;
    background: linear-gradient(180deg, var(--bg-elevated), var(--bg-card));

    span {
        color: var(--text-tertiary);
        font-size: 12px;
        font-weight: 700;
    }

    strong {
        color: var(--text-primary);
        font-size: 22px;
        font-weight: 800;
        line-height: 1.15;
    }

    small {
        color: var(--text-tertiary);
        font-size: 12px;
        line-height: 1.45;
    }
}

.group-tree-list {
    display: grid;
    gap: 14px;
    padding: 16px 16px 18px;
}

.group-tree-card {
    display: grid;
    gap: 12px;
    padding: 14px;
    border: 1px solid var(--border-light);
    border-radius: 14px;
    background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.02), transparent),
        var(--bg-card);
    box-shadow: var(--shadow-sm);
    transition:
        transform 0.18s ease,
        border-color 0.18s ease,
        box-shadow 0.18s ease;
}

.group-tree-card:hover {
    transform: translateY(-1px);
    border-color: color-mix(in srgb, var(--primary) 20%, var(--border-light));
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.group-tree-card__head {
    justify-content: space-between;
    gap: 14px;
    min-width: 0;
}

.group-tree-toggle {
    flex: 1 1 auto;
    gap: 12px;
    min-width: 0;
    border: 0;
    background: transparent;
    cursor: pointer;
    text-align: left;
}

.group-tree-toggle__icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    flex: 0 0 32px;
    border: 1px solid var(--border-color-light);
    border-radius: 999px;
    color: var(--primary);
    background: var(--bg-elevated);
}

.group-tree-copy {
    display: grid;
    gap: 8px;
    min-width: 0;
}

.group-tree-title-line {
    gap: 10px;
    min-width: 0;
    flex-wrap: wrap;

    h3 {
        margin: 0;
        color: var(--text-primary);
        font-size: 16px;
        font-weight: 800;
        line-height: 1.35;
    }
}

.group-tree-subject {
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 700;
    white-space: nowrap;
}

.group-tree-meta {
    flex-wrap: wrap;
    gap: 8px 10px;
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 600;
}

.group-tree-actions {
    flex: 0 0 auto;
}

.group-tree-children {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 12px;
    padding-top: 2px;
}

.group-child-card {
    display: grid;
    gap: 10px;
    min-width: 0;
    padding: 12px 13px;
    border: 1px solid var(--border-color-light);
    border-radius: 12px;
    background: var(--bg-elevated);
    text-align: left;
    cursor: pointer;
    transition:
        transform 0.18s ease,
        border-color 0.18s ease,
        background-color 0.18s ease;
}

.group-child-card:hover {
    transform: translateY(-1px);
    border-color: color-mix(in srgb, var(--primary) 28%, var(--border-color-light));
    background: color-mix(in srgb, var(--primary) 4%, var(--bg-elevated));
}

.group-child-card__head,
.group-child-card__stats,
.group-child-card__footer {
    justify-content: space-between;
    gap: 10px;
}

.group-child-card__title {
    display: grid;
    gap: 4px;
    min-width: 0;

    strong {
        color: var(--text-primary);
        font-size: 14px;
        line-height: 1.35;
    }
}

.group-child-label {
    color: var(--text-tertiary);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
}

.group-child-card__stats,
.group-child-card__footer {
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 600;
}

.group-child-preview {
    display: grid;
    gap: 6px;
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.5;

    span {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
}

.overview-strip {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0;
    margin-top: 14px;
    border-top: 1px solid var(--border-light);
}

.overview-item {
    display: grid;
    gap: 4px;
    min-width: 0;
    padding: 12px 14px 0;
    border-left: 1px solid var(--border-color-light);

    &:first-child {
        border-left: 0;
        padding-left: 0;
    }

    span {
        color: var(--text-tertiary);
        font-size: 12px;
        font-weight: 700;
    }

    strong {
        color: var(--text-primary);
        font-size: 22px;
        font-weight: 800;
        line-height: 1.15;
    }

    small {
        color: var(--text-tertiary);
        font-size: 12px;
        line-height: 1.45;
    }
}

.group-list-table {
    min-width: 0;
}

.group-list-head,
.group-list-parent,
.group-list-child {
    display: grid;
    grid-template-columns: minmax(260px, 1.25fr) minmax(200px, 0.82fr) minmax(150px, 0.56fr) minmax(0, 1.45fr) 120px;
    gap: 14px;
    align-items: center;
}

.group-list-head {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-light);
    background: var(--table-header-bg);
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 700;
}

.group-list-group {
    border-bottom: 1px solid var(--border-light);
}

.group-list-parent {
    min-width: 0;
    padding: 14px 16px;
    background: var(--bg-card);
}

.group-list-parent__main {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    min-width: 0;
    width: 100%;
    border: 0;
    background: transparent;
    text-align: left;
    cursor: pointer;
}

.group-list-parent__icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    flex: 0 0 26px;
    margin-top: 1px;
    border: 1px solid var(--border-color-light);
    border-radius: 999px;
    color: var(--primary);
    background: var(--bg-elevated);
}

.group-list-parent__copy {
    display: grid;
    gap: 6px;
    min-width: 0;
}

.group-list-parent__title {
    align-items: baseline;
    min-width: 0;

    strong {
        color: var(--text-primary);
        font-size: 15px;
        font-weight: 800;
        line-height: 1.35;
    }

    span {
        color: var(--text-tertiary);
        font-size: 12px;
        font-weight: 700;
    }
}

.group-list-parent__meta {
    align-items: center;
    min-width: 0;
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 600;
}

.group-list-parent__status,
.group-list-parent__summary,
.group-list-parent__actions,
.group-list-child__status,
.group-list-child__meta,
.group-list-child__actions {
    display: flex;
    align-items: center;
}

.group-list-parent__status,
.group-list-parent__summary {
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 600;
}

.group-list-parent__preview {
    color: var(--text-tertiary);
    font-size: 12px;
    line-height: 1.55;
}

.group-list-parent__actions,
.group-list-child__actions {
    justify-content: flex-end;
}

.group-list-children {
    display: grid;
}

.group-list-child {
    min-width: 0;
    padding: 12px 16px 12px 28px;
    border-top: 1px dashed var(--border-color-light);
    background: color-mix(in srgb, var(--bg-elevated) 88%, var(--bg-card));
}

.group-list-child__name {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    min-width: 0;
    width: 100%;
    border: 0;
    background: transparent;
    text-align: left;
    cursor: pointer;
}

.group-list-child__branch {
    position: relative;
    width: 14px;
    height: 14px;
    flex: 0 0 14px;
    margin-top: 2px;

    &::before,
    &::after {
        content: "";
        position: absolute;
        background: color-mix(in srgb, var(--primary) 28%, var(--border-color-light));
    }

    &::before {
        top: 0;
        bottom: 6px;
        left: 6px;
        width: 1px;
    }

    &::after {
        top: 6px;
        left: 6px;
        width: 8px;
        height: 1px;
    }
}

.group-list-child__copy {
    display: grid;
    gap: 4px;
    min-width: 0;

    strong {
        color: var(--text-primary);
        font-size: 14px;
        font-weight: 700;
        line-height: 1.35;
    }

    span {
        color: var(--text-tertiary);
        font-size: 12px;
        font-weight: 600;
    }
}

.group-list-child__status,
.group-list-child__meta {
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 600;
}

.group-list-child__preview {
    display: grid;
    gap: 4px;
    min-width: 0;
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.55;

    span {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
}

.group-drawer-panel {
    display: grid;
    gap: 14px;
}

.group-summary-card,
.detail-card {
    border: 1px solid var(--border-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);
}

.group-summary-card {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(230px, 0.4fr);
    gap: 14px;
    padding: 14px;
    border-radius: 14px;
    background:
        radial-gradient(circle at top right, color-mix(in srgb, var(--primary) 8%, transparent), transparent 40%),
        var(--bg-card);
}

.group-summary-main {
    display: grid;
    align-content: start;
    gap: 10px;
    min-width: 0;

    h3 {
        margin: 0;
        color: var(--text-primary);
        font-size: 20px;
        font-weight: 800;
        line-height: 1.4;
    }
}

.group-summary-note {
    color: var(--text-tertiary);
    font-size: 13px;
    line-height: 1.6;
}

.group-summary-side {
    display: grid;
    gap: 8px;

    > div {
        display: grid;
        gap: 6px;
        min-width: 0;
        padding: 10px 12px;
        border: 1px solid var(--border-color-light);
        border-radius: 6px;
        background: var(--bg-elevated);
    }

    span {
        color: var(--text-tertiary);
        font-size: 12px;
        font-weight: 700;
    }

    strong {
        color: var(--text-primary);
        font-size: 13px;
        line-height: 1.4;
    }
}

.detail-card {
    display: grid;
    gap: 12px;
    min-width: 0;
    padding: 14px;
    border-radius: 14px;
}

.detail-card-header {
    justify-content: space-between;
    gap: 10px;
    color: var(--text-secondary);
    font-size: 14px;
    font-weight: 800;
}

.workbench-head {
    justify-content: space-between;
    gap: 14px;
    align-items: flex-start;
    flex-wrap: wrap;
}

.workbench-head__copy,
.keyword-workspace__copy {
    display: grid;
    gap: 4px;
    min-width: 0;
}

.workbench-head__tools {
    align-items: flex-start;
    justify-content: flex-end;
    margin-left: auto;
}

.drawer-search-input {
    width: min(360px, 44vw);
}

.category-editor-layout {
    display: grid;
    grid-template-columns: minmax(230px, 270px) minmax(0, 1fr);
    gap: 16px;
    min-width: 0;
    min-height: 520px;
}

.category-sidebar {
    display: grid;
    align-content: start;
    gap: 10px;
    max-height: 680px;
    overflow: auto;
    padding: 12px;
    border: 1px solid var(--border-color-light);
    border-radius: 12px;
    background: var(--bg-elevated);
}

.category-sidebar__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 0 2px 4px;
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 700;
}

.category-tab {
    display: grid;
    gap: 4px;
    width: 100%;
    padding: 10px 12px;
    border: 1px solid transparent;
    border-radius: 10px;
    color: var(--text-secondary);
    background: transparent;
    text-align: left;
    cursor: pointer;
}

.category-tab__copy {
    display: grid;
    gap: 6px;
    min-width: 0;
}

.category-tab__title,
.category-tab__meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    min-width: 0;
}

.category-tab__title span {
    color: inherit;
    font-size: 13px;
    font-weight: 800;
    line-height: 1.35;
}

.category-tab__meta small {
    color: var(--text-tertiary);
    font-size: 12px;
}

.category-tab.is-active {
    border-color: color-mix(in srgb, var(--primary) 32%, var(--border-color-light));
    color: var(--primary);
    background: color-mix(in srgb, var(--primary) 7%, var(--bg-card));
}

.keyword-workspace {
    display: grid;
    align-content: start;
    gap: 14px;
    min-width: 0;
    overflow: auto;
    padding: 16px;
    border: 1px solid var(--border-color-light);
    border-radius: 12px;
    background: var(--bg-card);
}

.keyword-workspace__head {
    justify-content: space-between;
    gap: 12px;
    min-width: 0;
    overflow: hidden;
    flex-wrap: wrap;
    align-items: flex-end;

    span {
        color: var(--text-tertiary);
        font-size: 12px;
        font-weight: 700;
    }

    strong {
        color: var(--text-primary);
        font-size: 16px;
        font-weight: 800;
        line-height: 1.35;
    }

    p {
        color: var(--text-tertiary);
        font-size: 12px;
        line-height: 1.5;
    }
}

.keyword-workspace__meta {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 700;
}

.add-keyword-btn {
    flex: 0 0 auto;
    white-space: nowrap;
}

.rule-card-list {
    display: grid;
    gap: 12px;
    min-width: 0;
}

.rule-card {
    display: grid;
    gap: 12px;
    min-width: 0;
    padding: 14px;
    border: 1px solid var(--border-color-light);
    border-radius: 12px;
    background: var(--bg-elevated);
}

.rule-card__head {
    justify-content: space-between;
    gap: 12px;
    min-width: 0;
}

.rule-card__title {
    display: grid;
    gap: 4px;
    min-width: 0;

    strong {
        color: var(--text-primary);
        font-size: 14px;
        line-height: 1.45;
    }
}

.rule-card__index {
    color: var(--text-tertiary);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
}

.rule-card__badges {
    flex-wrap: wrap;
    gap: 8px;
    justify-content: flex-end;
}

.rule-detail-grid,
.rule-editor-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px 12px;
    min-width: 0;
}

.rule-detail-block,
.rule-editor-field {
    display: grid;
    gap: 6px;
    min-width: 0;
}

.rule-detail-block span,
.rule-editor-field span {
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 700;
}

.rule-detail-block strong {
    color: var(--text-primary);
    font-size: 13px;
    line-height: 1.5;
    word-break: break-word;
}

.rule-editor-field--wide {
    grid-column: span 2;
}

.rule-delete-btn {
    align-self: end;
    justify-self: end;
}

.remark-condition-stack {
    display: grid;
    gap: 8px;
    min-width: 0;
}

.remark-condition-stack > :deep(.el-input) {
    width: 100%;
}

.condition-stack {
    display: grid;
    grid-template-columns: minmax(120px, 168px) minmax(0, 1fr);
    gap: 8px;
    align-items: center;
    min-width: 0;
}

.condition-stack--single {
    grid-template-columns: minmax(120px, 200px);
}

.condition-stack > :deep(.el-input),
.condition-stack > :deep(.el-select) {
    min-width: 0;
    width: 100%;
}

.drawer-footer {
    position: sticky;
    bottom: 0;
    z-index: 2;
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin: 20px -24px -20px;
    padding: 14px 24px;
    background: var(--bg-elevated);
    border-top: 1px solid var(--border-light);
}

@media (max-width: 1100px) {
    .page-toolbar,
    .workbench-head,
    .keyword-workspace__head,
    .group-tree-card__head {
        align-items: flex-start;
        flex-direction: column;
    }

    .overview-grid,
    .overview-strip {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .overview-item {
        padding-left: 0;
        border-left: 0;
    }

    .group-summary-card,
    .category-editor-layout {
        grid-template-columns: 1fr;
    }

    .rule-detail-grid,
    .rule-editor-grid {
        grid-template-columns: 1fr;
    }

    .rule-editor-field--wide {
        grid-column: auto;
    }

    .group-tree-children {
        grid-template-columns: 1fr;
    }

    .group-list-head {
        display: none;
    }

    .group-list-parent,
    .group-list-child {
        grid-template-columns: 1fr;
        gap: 10px;
    }

    .group-list-child {
        padding-left: 16px;
    }

    .group-list-parent__actions,
    .group-list-child__actions {
        justify-content: flex-start;
    }

    .group-search-input,
    .drawer-search-input {
        width: 100%;
    }

    .condition-stack,
    .condition-stack--single {
        grid-template-columns: 1fr;
    }

    .toolbar-actions,
    .workbench-head__tools,
    .toolbar-actions :deep(.el-button),
    .workbench-head__tools :deep(.el-button) {
        width: 100%;
        max-width: none;
    }
}
</style>

<style lang="scss">
.reclass-drawer {
    .el-drawer__body {
        display: flex;
        flex-direction: column;
        overflow: auto;
    }
}
</style>
