<template>
    <div class="page-container reclass-page">
        <el-card shadow="never" class="table-card rule-table-card">
            <template #header>
                <div class="page-toolbar">
                    <div class="title-stack">
                        <span class="page-kicker">TRANSACTION RECLASS</span>
                        <div class="title-row">
                            <h2>动账重分类</h2>
                            <span class="count-text">共 {{ ruleGroups.length }} 条</span>
                        </div>
                    </div>
                    <div class="toolbar-actions">
                        <el-button @click="loadData">
                            <el-icon><Refresh /></el-icon>
                            刷新
                        </el-button>
                    </div>
                </div>
            </template>

            <el-table
                class="summary-table roomy-table reclass-group-table"
                :data="ruleGroups"
                v-loading="loading"
                stripe
                border
                style="width: 100%"
                height="calc(100vh - 215px)"
            >
                <el-table-column label="序号" width="70" align="center" fixed="left">
                    <template #default="{ $index }">{{ $index + 1 }}</template>
                </el-table-column>
                <el-table-column label="科目" min-width="260" show-overflow-tooltip>
                    <template #default="{ row }">
                        <span class="subject-name">{{ row.subjectName }}</span>
                    </template>
                </el-table-column>
                <el-table-column label="平台" width="160">
                    <template #default="{ row }">
                        <PlatformBadge
                            v-if="row.platformCode"
                            :platform="row.platformCode"
                        />
                        <el-tag v-else size="small" effect="plain">通用</el-tag>
                    </template>
                </el-table-column>
                <el-table-column label="更新时间" width="180">
                    <template #default="{ row }">{{ formatDateTime(row.updatedAt) }}</template>
                </el-table-column>
                <el-table-column label="状态" width="120" align="center">
                    <template #default="{ row }">
                        <el-tag :type="groupStatusType(row.status)" size="small">
                            {{ groupStatusLabel(row.status) }}
                        </el-tag>
                    </template>
                </el-table-column>
                <el-table-column label="操作" width="150" fixed="right" align="center">
                    <template #default="{ row }">
                        <el-button type="primary" link @click="openGroupDetail(row)">查看</el-button>
                        <el-button type="primary" link @click="openGroupEditor(row)">编辑</el-button>
                    </template>
                </el-table-column>

                <template #empty>
                    <el-empty description="暂无动账重分类" :image-size="80" />
                </template>
            </el-table>
        </el-card>

        <el-drawer
            v-model="drawerVisible"
            :title="drawerTitle"
            size="min(980px, 92vw)"
            class="reclass-drawer"
            append-to-body
            destroy-on-close
            :close-on-click-modal="false"
        >
            <div v-if="selectedGroup" class="group-drawer-panel">
                <section class="group-summary-card">
                    <div class="group-summary-main">
                        <span class="detail-kicker">SUBJECT #{{ selectedGroup.subjectId }}</span>
                        <h3>{{ selectedGroup.subjectName }}</h3>
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
                    <div class="detail-card-header">
                        <span>重分类关键词</span>
                        <span>{{ visibleCategoryPanels.length }} 类 · {{ visibleKeywordTotal }} 词</span>
                    </div>

                    <el-input
                        v-model="drawerSearchText"
                        clearable
                        class="drawer-search-input"
                        placeholder="搜索重分类或关键词"
                    >
                        <template #prefix>
                            <el-icon><Search /></el-icon>
                        </template>
                    </el-input>

                    <div v-if="visibleCategoryPanels.length" class="category-editor-layout">
                        <aside class="category-sidebar" aria-label="重分类列表">
                            <button
                                v-for="panel in visibleCategoryPanels"
                                :key="panel.categoryId"
                                type="button"
                                class="category-tab"
                                :class="{ 'is-active': activeCategoryPanel?.categoryId === panel.categoryId }"
                                @click="setActiveCategory(panel.categoryId)"
                            >
                                <span>{{ panel.categoryName }}</span>
                                <small>{{ panel.keywords.length }} 词</small>
                            </button>
                        </aside>

                        <section
                            v-if="activeCategoryPanel"
                            class="keyword-workspace"
                            aria-label="当前重分类关键词"
                        >
                            <div class="keyword-workspace__head">
                                <div>
                                    <span>当前重分类</span>
                                    <strong>{{ activeCategoryPanel.categoryName }}</strong>
                                </div>
                                <el-button
                                    v-if="drawerMode === 'edit'"
                                    class="add-keyword-btn"
                                    type="primary"
                                    link
                                    @click="addKeywordToActiveCategory"
                                >
                                    <el-icon><Plus /></el-icon>
                                    添加关键词
                                </el-button>
                            </div>

                            <div v-if="activeKeywordItems.length" class="keyword-list-head">
                                <span>关键词</span>
                                <span>出入账方向</span>
                                <span>表头</span>
                                <span>取值</span>
                            </div>

                            <div v-if="activeKeywordItems.length" class="keyword-input-grid">
                                <div
                                    v-for="item in activeKeywordItems"
                                    :key="item.key"
                                    class="keyword-input-row"
                                    :class="`keyword-input-row--${drawerMode}`"
                                >
                                    <div v-if="drawerMode === 'detail'" class="readonly-keyword">
                                        {{ item.value }}
                                    </div>
                                    <el-input
                                        v-else
                                        v-model="item.value"
                                        maxlength="1000"
                                        clearable
                                        placeholder="输入关键词"
                                    />
                                    <div v-if="drawerMode === 'detail'" class="readonly-field">
                                        {{ item.transactionDirection }}
                                    </div>
                                    <el-select
                                        v-else
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
                                    <div v-if="drawerMode === 'detail'" class="readonly-field">
                                        {{ item.amountField }}
                                    </div>
                                    <el-input
                                        v-else
                                        v-model="item.amountField"
                                        maxlength="100"
                                        clearable
                                        placeholder="输入表头"
                                    />
                                    <div v-if="drawerMode === 'detail'" class="readonly-field">
                                        {{ resultDirectionLabel(item.resultDirection) }}
                                    </div>
                                    <el-select
                                        v-else
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
                                    <el-button
                                        v-if="drawerMode === 'edit'"
                                        circle
                                        text
                                        type="danger"
                                        aria-label="删除关键词"
                                        @click="removeKeyword(activeCategoryPanel.categoryId, item.key)"
                                    >
                                        <el-icon><Close /></el-icon>
                                    </el-button>
                                </div>
                            </div>

                            <el-empty
                                v-else
                                description="当前重分类暂无关键词"
                                :image-size="80"
                            />
                        </section>
                    </div>

                    <el-empty
                        v-else
                        description="没有匹配的重分类或关键词"
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
}

interface KeywordItem {
    key: number;
    ruleId?: number;
    value: string;
    transactionDirection: string;
    amountField: string;
    resultDirection: TransactionRule["result_direction"];
    sourceRule?: TransactionRule;
    deleted?: boolean;
}

interface CategoryPanel {
    categoryId: number;
    categoryName: string;
    sortOrder: number;
    keywords: KeywordItem[];
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
const categoryForms = ref<CategoryPanel[]>([]);
const groupStatusValue = ref<0 | 1>(1);
const keySeed = ref(1);

const transactionDirectionOptions = [
    { label: "入账", value: "入账" },
    { label: "出账", value: "出账" },
];

const resultDirectionSelectOptions: Array<{
    label: string;
    value: TransactionRule["result_direction"];
}> = [
    { label: "原值", value: "original" },
    { label: "取正", value: "positive" },
    { label: "取负", value: "negative" },
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
        });
    });

    return Array.from(groupMap.values())
        .map((group) => ({
            ...group,
            status: resolveGroupStatus(group.rules),
        }))
        .sort(
            (a, b) =>
                subjectSortOrder(a.subjectId) - subjectSortOrder(b.subjectId) ||
                a.subjectName.localeCompare(b.subjectName, "zh-Hans-CN") ||
                platformLabel(a.platformCode).localeCompare(platformLabel(b.platformCode), "zh-Hans-CN"),
        );
});

const selectedGroup = computed(() =>
    ruleGroups.value.find((group) => group.key === selectedGroupKey.value) || null,
);

const drawerTitle = computed(() =>
    drawerMode.value === "edit" ? "编辑动账重分类" : "动账重分类详情",
);

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
            keywords: activeKeywords(panel),
        }))
        .filter((panel) => drawerMode.value === "edit" || panel.keywords.length);

    if (!query) return panels;

    return panels
        .map((panel) => {
            const categoryMatched = panel.categoryName.toLowerCase().includes(query);
            const keywords = categoryMatched
                ? panel.keywords
                : panel.keywords.filter((item) => item.value.toLowerCase().includes(query));
            return { ...panel, keywords };
        })
        .filter((panel) => panel.keywords.length || panel.categoryName.toLowerCase().includes(query));
});

const activeCategoryPanel = computed(() => {
    if (!visibleCategoryPanels.value.length) return null;
    return (
        visibleCategoryPanels.value.find((panel) => panel.categoryId === activeCategoryId.value) ||
        visibleCategoryPanels.value[0]
    );
});

const activeKeywordItems = computed(() => activeCategoryPanel.value?.keywords || []);
const visibleKeywordTotal = computed(() =>
    visibleCategoryPanels.value.reduce((total, panel) => total + panel.keywords.length, 0),
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
    nextTick(ensureActiveCategory);
}

function openGroupEditor(group: RuleGroup) {
    drawerMode.value = "edit";
    selectedGroupKey.value = group.key;
    drawerSearchText.value = "";
    groupStatusValue.value = group.status === "disabled" ? 0 : 1;
    categoryForms.value = buildCategoryPanels(group, true);
    drawerVisible.value = true;
    nextTick(ensureActiveCategory);
}

function ensureActiveCategory() {
    activeCategoryId.value = visibleCategoryPanels.value[0]?.categoryId ?? null;
}

function setActiveCategory(categoryId: number) {
    activeCategoryId.value = categoryId;
}

function addKeywordToActiveCategory() {
    const categoryId = activeCategoryPanel.value?.categoryId;
    if (!categoryId) return;
    const panel = categoryForms.value.find((item) => item.categoryId === categoryId);
    if (!panel) return;
    panel.keywords.push(createKeywordItem(undefined, panel.templateRule));
}

function removeKeyword(categoryId: number, key: number) {
    const panel = categoryForms.value.find((item) => item.categoryId === categoryId);
    if (!panel) return;
    const index = panel.keywords.findIndex((item) => item.key === key);
    if (index < 0) return;
    const item = panel.keywords[index];
    if (item.ruleId) {
        item.deleted = true;
    } else {
        panel.keywords.splice(index, 1);
    }
}

async function handleSubmitGroup() {
    const group = selectedGroup.value;
    if (!group) return;

    const hasKeyword = categoryForms.value.some((panel) =>
        activeKeywords(panel).some((item) => item.value.trim()),
    );
    if (!hasKeyword) {
        ElMessage.warning("至少保留一个关键词");
        return;
    }
    const missingHeader = categoryForms.value.some((panel) =>
        activeKeywords(panel).some((item) => item.value.trim() && !item.amountField.trim()),
    );
    if (missingHeader) {
        ElMessage.warning("请填写关键词对应的表头");
        return;
    }

    submitting.value = true;
    try {
        let nextPriority = Math.max(0, ...group.rules.map((rule) => rule.priority || 0)) + 10;
        for (const panel of categoryForms.value) {
            for (const item of panel.keywords) {
                const value = item.value.trim();
                if (item.ruleId) {
                    if (item.deleted || !value) {
                        await deleteTransactionRule(item.ruleId);
                        continue;
                    }

                    const source = item.sourceRule || findRule(item.ruleId);
                    if (!source) continue;
                    if (
                        value !== source.remark_pattern ||
                        item.transactionDirection !== source.transaction_direction ||
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
                            match_type: source.match_type || "exact",
                            remark_pattern: value,
                            amount_field: item.amountField.trim(),
                            result_direction: item.resultDirection,
                            priority: source.priority,
                            status: groupStatusValue.value,
                        });
                    }
                    continue;
                }

                if (!value) continue;
                const template = item.sourceRule || panel.templateRule || group.rules[0];
                await createTransactionRule({
                    subject_id: group.subjectId,
                    category_id: panel.categoryId,
                    platform_code: group.platformCode,
                    transaction_direction: item.transactionDirection,
                    remark_field: template?.remark_field || "备注",
                    direction_field: template?.direction_field || "动账方向",
                    match_type: template?.match_type || "exact",
                    remark_pattern: value,
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
                keywords: categoryRules.map((rule) => createKeywordItem(rule, rule)),
                templateRule: categoryRules[0] || group.rules[0],
            };
        })
        .filter((panel) => includeEmptyCategories || panel.keywords.length);
}

function createKeywordItem(rule?: TransactionRule, templateRule?: TransactionRule): KeywordItem {
    return {
        key: keySeed.value++,
        ruleId: rule?.id,
        value: rule?.remark_pattern || "",
        transactionDirection: rule?.transaction_direction || templateRule?.transaction_direction || "入账",
        amountField: rule?.amount_field || templateRule?.amount_field || "动账金额",
        resultDirection: rule?.result_direction || templateRule?.result_direction || "original",
        sourceRule: rule || templateRule,
        deleted: false,
    };
}

function activeKeywords(panel: CategoryPanel) {
    return panel.keywords.filter((item) => !item.deleted);
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
        padding: 16px 18px 12px;
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
.keyword-workspace__head {
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
.detail-badge-row {
    flex-wrap: wrap;
    gap: 8px;
}

.subject-name {
    color: var(--text-primary);
    font-size: 14px;
    font-weight: 700;
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
}

.group-summary-main {
    display: grid;
    align-content: start;
    gap: 10px;
    min-width: 0;

    h3 {
        margin: 0;
        color: var(--text-primary);
        font-size: 18px;
        font-weight: 700;
        line-height: 1.4;
    }
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
}

.detail-card-header {
    justify-content: space-between;
    gap: 10px;
    color: var(--text-secondary);
    font-size: 13px;
    font-weight: 700;
}

.drawer-search-input {
    max-width: 360px;
}

.category-editor-layout {
    display: grid;
    grid-template-columns: minmax(160px, 0.28fr) minmax(0, 1fr);
    gap: 12px;
    min-height: 480px;
    min-width: 0;
    overflow: hidden;
}

.category-sidebar {
    display: grid;
    align-content: start;
    gap: 8px;
    max-height: 520px;
    overflow: auto;
    padding: 10px;
    border: 1px solid var(--border-color-light);
    border-radius: 8px;
    background: var(--bg-elevated);
}

.category-tab {
    display: grid;
    gap: 4px;
    width: 100%;
    padding: 10px 12px;
    border: 1px solid transparent;
    border-radius: 6px;
    color: var(--text-secondary);
    background: transparent;
    text-align: left;
    cursor: pointer;

    span {
        color: inherit;
        font-size: 13px;
        font-weight: 700;
        line-height: 1.35;
    }

    small {
        color: var(--text-tertiary);
        font-size: 12px;
    }
}

.category-tab.is-active {
    border-color: color-mix(in srgb, var(--primary) 32%, var(--border-color-light));
    color: var(--primary);
    background: color-mix(in srgb, var(--primary) 9%, var(--bg-card));
}

.keyword-workspace {
    display: grid;
    align-content: start;
    gap: 12px;
    min-width: 0;
    overflow: hidden;
    padding: 12px;
    border: 1px solid var(--border-color-light);
    border-radius: 8px;
    background: var(--bg-card);
}

.keyword-workspace__head {
    justify-content: space-between;
    gap: 12px;
    min-width: 0;
    overflow: hidden;

    div {
        display: grid;
        gap: 4px;
        min-width: 0;
    }

    span {
        color: var(--text-tertiary);
        font-size: 12px;
        font-weight: 700;
    }

    strong {
        color: var(--text-primary);
        font-size: 15px;
        line-height: 1.35;
    }
}

.add-keyword-btn {
    flex: 0 0 auto;
    white-space: nowrap;
}

.keyword-list-head {
    display: grid;
    grid-template-columns: minmax(0, 1.1fr) minmax(78px, 0.34fr) minmax(0, 0.82fr) minmax(78px, 0.34fr) 28px;
    gap: 6px;
    align-items: center;
    min-width: 0;
    padding: 0 2px;
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 700;
}

.keyword-input-grid {
    display: grid;
    gap: 8px;
    min-width: 0;
}

.keyword-input-row {
    display: grid;
    gap: 6px;
    align-items: center;
    min-width: 0;
}

.keyword-input-row--detail,
.keyword-input-row--edit {
    grid-template-columns: minmax(0, 1.1fr) minmax(78px, 0.34fr) minmax(0, 0.82fr) minmax(78px, 0.34fr) 28px;
}

.keyword-input-row > :deep(.el-input),
.keyword-input-row > :deep(.el-select) {
    min-width: 0;
}

.keyword-input-row :deep(.el-input__wrapper),
.keyword-input-row :deep(.el-select__wrapper) {
    padding-left: 10px;
    padding-right: 8px;
}

.readonly-keyword,
.readonly-field {
    min-height: 34px;
    padding: 8px 10px;
    border: 1px solid var(--border-color-light);
    border-radius: 6px;
    color: var(--text-primary);
    background: var(--bg-elevated);
    font-size: 13px;
    line-height: 1.45;
    word-break: break-word;
}

.readonly-field {
    color: var(--text-secondary);
    word-break: keep-all;
}

.keyword-input-row :deep(.el-button.is-circle) {
    width: 28px;
    height: 28px;
}

.drawer-footer {
    position: sticky;
    bottom: 0;
    z-index: 2;
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin: 24px -20px -20px;
    padding: 14px 20px;
    background: var(--bg-elevated);
    border-top: 1px solid var(--border-light);
}

@media (max-width: 1100px) {
    .page-toolbar,
    .keyword-workspace__head {
        align-items: flex-start;
        flex-direction: column;
    }

    .group-summary-card,
    .category-editor-layout {
        grid-template-columns: 1fr;
    }

    .keyword-list-head {
        display: none;
    }

    .keyword-input-row--detail,
    .keyword-input-row--edit {
        grid-template-columns: 1fr;
    }

    .drawer-search-input,
    .toolbar-actions,
    .toolbar-actions :deep(.el-button) {
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
