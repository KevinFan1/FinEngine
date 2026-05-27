<template>
    <div class="page-container transaction-page split-rule-page">
        <el-card shadow="never" class="search-card">
            <div class="rule-toolbar">
                <SearchCardIntro
                    kicker="RULE TREE"
                    title="资金重分类规则"
                    tip="左侧只看科目和重分类，右侧专门维护当前重分类下的规则"
                />
                <div class="rule-toolbar__actions">
                    <el-input
                        v-model="searchText"
                        clearable
                        class="rule-search-input"
                        placeholder="搜索科目、重分类或规则"
                    >
                        <template #prefix>
                            <el-icon><Search /></el-icon>
                        </template>
                    </el-input>
                    <el-button @click="loadData">
                        <el-icon><Refresh /></el-icon>
                        刷新
                    </el-button>
                    <el-button type="primary" :disabled="isBusy" @click="startCreateSubject">
                        <el-icon><Plus /></el-icon>
                        新增科目
                    </el-button>
                </div>
            </div>

            <div class="rule-summary">
                共 {{ subjectNodes.length }} 个科目，{{ categories.length }} 个重分类，{{ rules.length }} 条规则
                <span v-if="searchText.trim()">
                    · 当前显示 {{ filteredCategoryCount }} 个重分类，{{ filteredRuleCount }} 条规则
                </span>
            </div>
        </el-card>

        <div v-loading="loading" class="rule-workspace">
            <el-card shadow="never" class="rule-tree-card">
                <template #header>
                    <div class="panel-header">
                        <div>
                            <span class="panel-header__title">层级</span>
                            <span class="panel-header__meta">科目 -> 重分类</span>
                        </div>
                        <span class="panel-header__count">
                            {{ filteredSubjectNodes.length }} 个科目
                        </span>
                    </div>
                </template>

                <div class="rule-tree">
                    <template v-if="filteredSubjectNodes.length">
                        <section
                            v-for="subject in filteredSubjectNodes"
                            :key="subject.key"
                            class="tree-group"
                        >
                            <div class="tree-row tree-row--subject">
                                <button
                                    type="button"
                                    class="tree-row__main"
                                    @click="toggleExpandedSubject(subject.key)"
                                >
                                    <span class="tree-row__icon">
                                        <el-icon v-if="subject.categories.length">
                                            <ArrowDown
                                                v-if="shouldExpandSubject(subject.key)"
                                            />
                                            <ArrowRight v-else />
                                        </el-icon>
                                    </span>
                                    <span class="tree-row__copy">
                                        <strong>{{ subject.subject.name }}</strong>
                                        <small>
                                            {{ subject.categories.length }} 个重分类 ·
                                            {{ subject.ruleCount }} 条规则
                                        </small>
                                    </span>
                                </button>

                                <el-dropdown
                                    trigger="click"
                                    @command="
                                        (command) =>
                                            handleSubjectCommand(subject, String(command))
                                    "
                                >
                                    <button
                                        type="button"
                                        class="tree-row__more"
                                        :disabled="isBusy"
                                    >
                                        ···
                                    </button>
                                    <template #dropdown>
                                        <el-dropdown-menu>
                                            <el-dropdown-item command="create-category">
                                                新增重分类
                                            </el-dropdown-item>
                                            <el-dropdown-item command="rename">
                                                改名
                                            </el-dropdown-item>
                                            <el-dropdown-item command="delete">
                                                删除
                                            </el-dropdown-item>
                                        </el-dropdown-menu>
                                    </template>
                                </el-dropdown>
                            </div>

                            <div
                                v-if="shouldExpandSubject(subject.key)"
                                class="tree-group__children"
                            >
                                <div
                                    v-for="category in subject.categories"
                                    :key="category.key"
                                    class="tree-row tree-row--category"
                                    :class="{
                                        'is-active': activeCategoryKey === category.key,
                                    }"
                                >
                                    <button
                                        type="button"
                                        class="tree-row__main tree-row__main--category"
                                        @click="selectCategory(category.key)"
                                    >
                                        <span class="tree-row__copy">
                                            <strong>{{ category.category.name }}</strong>
                                            <small>{{ categoryRuleText(category) }}</small>
                                        </span>
                                    </button>

                                    <el-dropdown
                                        trigger="click"
                                        @command="
                                            (command) =>
                                                handleCategoryCommand(
                                                    subject,
                                                    category,
                                                    String(command),
                                                )
                                        "
                                    >
                                        <button
                                            type="button"
                                            class="tree-row__more"
                                            :disabled="isBusy"
                                        >
                                            ···
                                        </button>
                                        <template #dropdown>
                                            <el-dropdown-menu>
                                                <el-dropdown-item command="create-rule">
                                                    新增规则
                                                </el-dropdown-item>
                                                <el-dropdown-item command="rename">
                                                    改名
                                                </el-dropdown-item>
                                                <el-dropdown-item command="delete">
                                                    删除
                                                </el-dropdown-item>
                                            </el-dropdown-menu>
                                        </template>
                                    </el-dropdown>
                                </div>

                                <div
                                    v-if="!subject.categories.length"
                                    class="tree-empty-row"
                                >
                                    暂无重分类
                                </div>
                            </div>
                        </section>
                    </template>

                    <el-empty
                        v-else
                        :description="
                            searchText.trim() ? '没有匹配到层级节点' : '暂无资金重分类规则'
                        "
                        :image-size="80"
                    />
                </div>
            </el-card>

            <el-card shadow="never" class="rule-detail-card">
                <template #header>
                    <div v-if="activeCategoryContext" class="detail-header">
                        <div class="detail-header__copy">
                            <span class="detail-header__eyebrow">
                                {{ activeCategoryContext.subject.subject.name }}
                            </span>
                            <strong>{{ activeCategoryContext.category.category.name }}</strong>
                            <small>{{ activeCategorySummary }}</small>
                        </div>
                        <div class="detail-header__actions">
                            <el-button
                                type="primary"
                                :disabled="isBusy"
                                @click="
                                    startCreateRule(
                                        activeCategoryContext.subject,
                                        activeCategoryContext.category,
                                    )
                                "
                            >
                                新增规则
                            </el-button>
                        </div>
                    </div>

                    <div v-else class="panel-header">
                        <div>
                            <span class="panel-header__title">规则</span>
                            <span class="panel-header__meta">请选择左侧重分类</span>
                        </div>
                    </div>
                </template>

                <div v-if="activeCategoryContext" class="rule-list">
                    <div class="rule-list__head">
                        <span>平台</span>
                        <span>规则说明</span>
                        <span>取值表头</span>
                        <span>结果</span>
                        <span>操作</span>
                    </div>

                    <div
                        v-if="isCreatingRuleForActiveCategory"
                        class="rule-list__row rule-list__row--editing"
                    >
                        <div class="rule-list__platform">
                            {{ platformLabel(editingDraft.platform_code) }}
                        </div>
                        <div class="rule-list__condition">
                            <div class="rule-editor">
                                <span>方向</span>
                                <el-select
                                    v-model="editingDraft.transaction_direction"
                                    size="small"
                                    class="rule-editor__field rule-editor__field--xs"
                                >
                                    <el-option
                                        v-for="item in directionOptions"
                                        :key="item.value"
                                        :label="item.label"
                                        :value="item.value"
                                    />
                                </el-select>

                                <span>场景</span>
                                <el-input
                                    v-model="editingDraft.transaction_scene"
                                    size="small"
                                    class="rule-editor__field rule-editor__field--sm"
                                    placeholder="可留空"
                                />

                                <span>备注条件</span>
                                <el-select
                                    v-model="editingDraft.match_type"
                                    size="small"
                                    class="rule-editor__field rule-editor__field--xs"
                                >
                                    <el-option
                                        v-for="item in ruleMatchOptions"
                                        :key="item.value"
                                        :label="item.label"
                                        :value="item.value"
                                    />
                                </el-select>
                                <el-input
                                    v-model="editingDraft.remark_pattern"
                                    size="small"
                                    class="rule-editor__field rule-editor__field--sm"
                                    placeholder="输入备注内容"
                                />
                            </div>
                        </div>
                        <div class="rule-list__amount">
                            <el-input
                                v-model="editingDraft.amount_field"
                                size="small"
                                class="rule-editor__field rule-editor__field--md"
                                placeholder="动账金额"
                            />
                        </div>
                        <div class="rule-list__result">
                            <el-select
                                v-model="editingDraft.result_direction"
                                size="small"
                                class="rule-editor__field rule-editor__field--sm"
                            >
                                <el-option
                                    v-for="item in resultDirectionOptions"
                                    :key="item.value"
                                    :label="item.label"
                                    :value="item.value"
                                />
                            </el-select>
                        </div>
                        <div class="rule-list__actions">
                            <el-button type="primary" link @click="saveEditingRow">
                                保存
                            </el-button>
                            <el-button link @click="cancelEditing">取消</el-button>
                        </div>
                    </div>

                    <template
                        v-for="rule in activeCategoryContext.category.rules"
                        :key="rule.id"
                    >
                        <div
                            class="rule-list__row"
                            :class="{ 'rule-list__row--editing': isEditingRule(rule) }"
                        >
                            <template v-if="isEditingRule(rule)">
                                <div class="rule-list__platform">
                                    {{ platformLabel(editingDraft.platform_code) }}
                                </div>
                                <div class="rule-list__condition">
                                    <div class="rule-editor">
                                        <span>方向</span>
                                        <el-select
                                            v-model="editingDraft.transaction_direction"
                                            size="small"
                                            class="rule-editor__field rule-editor__field--xs"
                                        >
                                            <el-option
                                                v-for="item in directionOptions"
                                                :key="item.value"
                                                :label="item.label"
                                                :value="item.value"
                                            />
                                        </el-select>

                                        <span>场景</span>
                                        <el-input
                                            v-model="editingDraft.transaction_scene"
                                            size="small"
                                            class="rule-editor__field rule-editor__field--sm"
                                            placeholder="可留空"
                                        />

                                        <span>备注条件</span>
                                        <el-select
                                            v-model="editingDraft.match_type"
                                            size="small"
                                            class="rule-editor__field rule-editor__field--xs"
                                        >
                                            <el-option
                                                v-for="item in ruleMatchOptions"
                                                :key="item.value"
                                                :label="item.label"
                                                :value="item.value"
                                            />
                                        </el-select>
                                        <el-input
                                            v-model="editingDraft.remark_pattern"
                                            size="small"
                                            class="rule-editor__field rule-editor__field--sm"
                                            placeholder="输入备注内容"
                                        />
                                    </div>
                                </div>
                                <div class="rule-list__amount">
                                    <el-input
                                        v-model="editingDraft.amount_field"
                                        size="small"
                                        class="rule-editor__field rule-editor__field--md"
                                        placeholder="动账金额"
                                    />
                                </div>
                                <div class="rule-list__result">
                                    <el-select
                                        v-model="editingDraft.result_direction"
                                        size="small"
                                        class="rule-editor__field rule-editor__field--sm"
                                    >
                                        <el-option
                                            v-for="item in resultDirectionOptions"
                                            :key="item.value"
                                            :label="item.label"
                                            :value="item.value"
                                        />
                                    </el-select>
                                </div>
                                <div class="rule-list__actions">
                                    <el-button type="primary" link @click="saveEditingRow">
                                        保存
                                    </el-button>
                                    <el-button link @click="cancelEditing">取消</el-button>
                                </div>
                            </template>

                            <template v-else>
                                <div class="rule-list__platform">
                                    {{ platformLabel(rule.platform_code) }}
                                </div>
                                <div class="rule-list__condition">
                                    <div class="rule-summary-text">
                                        <strong>{{ ruleDirectionSentence(rule) }}</strong>
                                        <span>{{ ruleRemarkSentence(rule) }}</span>
                                    </div>
                                </div>
                                <div class="rule-list__amount">
                                    {{ rule.amount_field || "动账金额" }}
                                </div>
                                <div class="rule-list__result">
                                    {{ resultDirectionText(rule.result_direction) }}
                                </div>
                                <div class="rule-list__actions">
                                    <el-button
                                        type="primary"
                                        link
                                        :disabled="isBusy"
                                        @click="startEditRule(rule)"
                                    >
                                        编辑
                                    </el-button>
                                    <el-button
                                        type="danger"
                                        link
                                        :disabled="isBusy"
                                        @click="removeRule(rule)"
                                    >
                                        删除
                                    </el-button>
                                </div>
                            </template>
                        </div>
                    </template>

                    <el-empty
                        v-if="
                            !activeCategoryContext.category.rules.length &&
                            !isCreatingRuleForActiveCategory
                        "
                        description="当前重分类暂无规则"
                        :image-size="80"
                    />
                </div>

                <div v-else class="rule-detail-empty">
                    <el-empty
                        description="请先在左侧选择一个重分类"
                        :image-size="80"
                    />
                </div>
            </el-card>
        </div>

        <el-dialog
            v-model="nodeDialogVisible"
            :title="nodeDialogTitle"
            width="420px"
            destroy-on-close
        >
            <div class="node-dialog">
                <el-input
                    v-model="nodeEditingDraft.name"
                    maxlength="100"
                    :placeholder="nodeDialogPlaceholder"
                    @keyup.enter="saveNodeEditor"
                />
                <p class="node-dialog__tip">{{ nodeDialogTip }}</p>
            </div>

            <template #footer>
                <el-button @click="nodeDialogVisible = false">取消</el-button>
                <el-button type="primary" @click="saveNodeEditor">保存</el-button>
            </template>
        </el-dialog>
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "TransactionRules" });

import { computed, onMounted, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import SearchCardIntro from "@/components/SearchCardIntro.vue";
import { usePageRefresh } from "@/composables/pageRefresh";
import { getPlatformList, type Platform } from "@/api/platform";
import {
    createTransactionCategory,
    createTransactionRule,
    createTransactionSubject,
    deleteTransactionCategory,
    deleteTransactionRule,
    deleteTransactionSubject,
    listTransactionCategories,
    listTransactionRules,
    listTransactionSubjects,
    updateTransactionCategory,
    updateTransactionRule,
    updateTransactionSubject,
    type TransactionCategory,
    type TransactionRule,
    type TransactionSubject,
} from "@/api/transactionAccounting";
import { directionOptions, resultDirectionOptions } from "./common";
import { getFallbackPlatforms } from "@/utils/platform";

type RuleMatchType = "none" | "exact" | "contains" | "not_contains";

type SubjectNode = {
    key: string;
    subject: TransactionSubject;
    categories: CategoryNode[];
    ruleCount: number;
};

type CategoryNode = {
    key: string;
    category: TransactionCategory;
    rules: TransactionRule[];
};

type CategoryContext = {
    subject: SubjectNode;
    category: CategoryNode;
};

type SubjectDraft = {
    name: string;
};

type CategoryDraft = {
    name: string;
};

type RuleDraft = {
    subject_id: number;
    category_id: number;
    platform_code: string | null;
    transaction_direction: string;
    transaction_scene: string;
    match_type: RuleMatchType;
    remark_pattern: string;
    result_direction: TransactionRule["result_direction"];
    priority: number;
    status: number;
    remark_field: string;
    direction_field: string;
    amount_field: string;
    remark_exclude_pattern: string;
};

type RuleEditingState =
    | {
          kind: "rule";
          mode: "create";
          parentKey: string;
          draft: RuleDraft;
      }
    | {
          kind: "rule";
          mode: "edit";
          rowKey: string;
          ruleId: number;
          draft: RuleDraft;
      };

type NodeEditorState =
    | {
          kind: "subject";
          mode: "create";
          draft: SubjectDraft;
      }
    | {
          kind: "subject";
          mode: "edit";
          subjectId: number;
          draft: SubjectDraft;
      }
    | {
          kind: "category";
          mode: "create";
          parentSubjectId: number;
          draft: CategoryDraft;
      }
    | {
          kind: "category";
          mode: "edit";
          categoryId: number;
          draft: CategoryDraft;
      };

const ruleMatchOptions: Array<{ label: string; value: RuleMatchType }> = [
    { label: "等于", value: "exact" },
    { label: "包含", value: "contains" },
    { label: "不包含", value: "not_contains" },
    { label: "不限", value: "none" },
];

const loading = ref(false);
const searchText = ref("");
const subjects = ref<TransactionSubject[]>([]);
const categories = ref<TransactionCategory[]>([]);
const rules = ref<TransactionRule[]>([]);
const platforms = ref<Platform[]>(getFallbackPlatforms());
const editingState = ref<RuleEditingState | null>(null);
const nodeEditor = ref<NodeEditorState | null>(null);
const expandedSubjectKeys = ref<string[]>([]);
const expansionInitialized = ref(false);
const activeCategoryKey = ref<string | null>(null);

const editingDraft = computed<any>(() => editingState.value?.draft ?? {});
const nodeEditingDraft = computed<any>(() => nodeEditor.value?.draft ?? {});
const forceExpandAll = computed(() => Boolean(searchText.value.trim()));
const isBusy = computed(
    () => Boolean(editingState.value) || Boolean(nodeEditor.value),
);
const nodeDialogVisible = computed({
    get: () => Boolean(nodeEditor.value),
    set: (visible: boolean) => {
        if (!visible) {
            nodeEditor.value = null;
        }
    },
});

const subjectNodes = computed<SubjectNode[]>(() => {
    const ruleMap = new Map<number, TransactionRule[]>();
    rules.value
        .slice()
        .sort((left, right) => left.priority - right.priority || left.id - right.id)
        .forEach((rule) => {
            const bucket = ruleMap.get(rule.category_id) || [];
            bucket.push(rule);
            ruleMap.set(rule.category_id, bucket);
        });

    const categoryMap = new Map<number, CategoryNode[]>();
    categories.value
        .slice()
        .sort(
            (left, right) =>
                Number(left.sort_order || 0) - Number(right.sort_order || 0) ||
                left.id - right.id,
        )
        .forEach((category) => {
            const bucket = categoryMap.get(category.subject_id) || [];
            bucket.push({
                key: categoryKey(category.id),
                category,
                rules: (ruleMap.get(category.id) || []).filter(
                    (rule) => rule.subject_id === category.subject_id,
                ),
            });
            categoryMap.set(category.subject_id, bucket);
        });

    return subjects.value
        .slice()
        .sort(
            (left, right) =>
                Number(left.sort_order || 0) - Number(right.sort_order || 0) ||
                left.id - right.id,
        )
        .map((subject) => {
            const subjectCategories = categoryMap.get(subject.id) || [];
            return {
                key: subjectKey(subject.id),
                subject,
                categories: subjectCategories,
                ruleCount: subjectCategories.reduce(
                    (sum, item) => sum + item.rules.length,
                    0,
                ),
            };
        });
});

const filteredSubjectNodes = computed<SubjectNode[]>(() => {
    const keyword = normalizeKeyword(searchText.value);
    if (!keyword) return subjectNodes.value;
    return subjectNodes.value
        .map((subject) => filterSubjectNode(subject, keyword))
        .filter((subject): subject is SubjectNode => Boolean(subject));
});

const categoryContexts = computed(() => flattenCategoryContexts(subjectNodes.value));
const filteredCategoryContexts = computed(() =>
    flattenCategoryContexts(filteredSubjectNodes.value),
);
const filteredCategoryCount = computed(() => filteredCategoryContexts.value.length);
const filteredRuleCount = computed(() =>
    filteredCategoryContexts.value.reduce(
        (sum, item) => sum + item.category.rules.length,
        0,
    ),
);

const activeCategoryContext = computed<CategoryContext | null>(() => {
    if (!filteredCategoryContexts.value.length) return null;
    return (
        filteredCategoryContexts.value.find(
            (item) => item.category.key === activeCategoryKey.value,
        ) || filteredCategoryContexts.value[0]
    );
});

const activeCategoryFullContext = computed<CategoryContext | null>(() => {
    const categoryId = activeCategoryContext.value?.category.category.id;
    if (!categoryId) return null;
    return (
        categoryContexts.value.find(
            (item) => item.category.category.id === categoryId,
        ) || null
    );
});

const activeCategorySummary = computed(() => {
    if (!activeCategoryContext.value) return "";
    const visibleCount = activeCategoryContext.value.category.rules.length;
    const totalCount = activeCategoryFullContext.value?.category.rules.length ?? visibleCount;
    return totalCount === visibleCount
        ? `${totalCount} 条规则`
        : `显示 ${visibleCount} / 共 ${totalCount} 条规则`;
});

const isCreatingRuleForActiveCategory = computed(
    () =>
        editingState.value?.kind === "rule" &&
        editingState.value.mode === "create" &&
        editingState.value.parentKey === activeCategoryContext.value?.category.key,
);

const nodeDialogTitle = computed(() => {
    if (!nodeEditor.value) return "";
    if (nodeEditor.value.kind === "subject") {
        return nodeEditor.value.mode === "create" ? "新增科目" : "修改科目名称";
    }
    return nodeEditor.value.mode === "create" ? "新增重分类" : "修改重分类名称";
});

const nodeDialogPlaceholder = computed(() => {
    if (!nodeEditor.value) return "";
    return nodeEditor.value.kind === "subject" ? "输入科目名称" : "输入重分类名称";
});

const nodeDialogTip = computed(() => {
    if (!nodeEditor.value) return "";
    if (nodeEditor.value.kind === "subject") {
        return nodeEditor.value.mode === "create"
            ? "新建后可以继续添加重分类和规则。"
            : "这里只能修改科目名称。";
    }
    return nodeEditor.value.mode === "create"
        ? "新重分类会挂在当前科目下。"
        : "这里只能修改重分类名称。";
});

watch(
    filteredCategoryContexts,
    (contexts) => {
        const hasSelection = contexts.some(
            (item) => item.category.key === activeCategoryKey.value,
        );
        if (!hasSelection) {
            activeCategoryKey.value = contexts[0]?.category.key ?? null;
        }
    },
    { immediate: true },
);

function subjectKey(subjectId: number) {
    return `subject:${subjectId}`;
}

function categoryKey(categoryId: number) {
    return `category:${categoryId}`;
}

function ruleKey(ruleId: number) {
    return `rule:${ruleId}`;
}

function flattenCategoryContexts(items: SubjectNode[]) {
    return items.flatMap((subject) =>
        subject.categories.map((category) => ({ subject, category })),
    );
}

function normalizeKeyword(value: string | null | undefined) {
    return String(value || "").trim().toLowerCase();
}

function matchesKeyword(keyword: string, ...values: Array<string | null | undefined>) {
    return values.some((value) => normalizeKeyword(value).includes(keyword));
}

function filterSubjectNode(subject: SubjectNode, keyword: string): SubjectNode | null {
    const matchedCategories = subject.categories
        .map((category) => filterCategoryNode(category, keyword))
        .filter((category): category is CategoryNode => Boolean(category));
    if (
        matchesKeyword(
            keyword,
            subject.subject.name,
            subject.subject.cash_flow_item_name,
        )
    ) {
        return subject;
    }
    if (!matchedCategories.length) return null;
    return {
        ...subject,
        categories: matchedCategories,
        ruleCount: matchedCategories.reduce(
            (sum, item) => sum + item.rules.length,
            0,
        ),
    };
}

function filterCategoryNode(category: CategoryNode, keyword: string): CategoryNode | null {
    const matchedRules = category.rules.filter((rule) =>
        matchesKeyword(
            keyword,
            category.category.name,
            rule.transaction_direction,
            rule.transaction_scene,
            rule.remark_pattern,
            rule.amount_field,
            platformLabel(rule.platform_code),
            resultDirectionText(rule.result_direction),
        ),
    );
    if (matchesKeyword(keyword, category.category.name)) {
        return category;
    }
    if (!matchedRules.length) return null;
    return {
        ...category,
        rules: matchedRules,
    };
}

function shouldExpandSubject(key: string) {
    return forceExpandAll.value || expandedSubjectKeys.value.includes(key);
}

function toggleExpandedSubject(key: string) {
    expandedSubjectKeys.value = expandedSubjectKeys.value.includes(key)
        ? expandedSubjectKeys.value.filter((item) => item !== key)
        : [...expandedSubjectKeys.value, key];
}

function selectCategory(key: string) {
    activeCategoryKey.value = key;
}

function categoryRuleText(category: CategoryNode) {
    const total = categoryContexts.value.find(
        (item) => item.category.category.id === category.category.id,
    )?.category.rules.length;
    if (!total || total === category.rules.length) {
        return `${category.rules.length} 条规则`;
    }
    return `${category.rules.length} / ${total} 条规则`;
}

function handleSubjectCommand(subject: SubjectNode, command: string) {
    if (command === "create-category") {
        startCreateCategory(subject);
        return;
    }
    if (command === "rename") {
        startEditSubject(subject);
        return;
    }
    if (command === "delete") {
        void removeSubject(subject);
    }
}

function handleCategoryCommand(
    subject: SubjectNode,
    category: CategoryNode,
    command: string,
) {
    if (command === "create-rule") {
        startCreateRule(subject, category);
        return;
    }
    if (command === "rename") {
        startEditCategory(category);
        return;
    }
    if (command === "delete") {
        void removeCategory(category);
    }
}

function platformLabel(platformCode?: string | null) {
    if (!platformCode) return "通用";
    return (
        platforms.value.find((item) => item.code === platformCode)?.name ||
        platformCode
    );
}

function resultDirectionText(value: TransactionRule["result_direction"]) {
    return (
        resultDirectionOptions.find((item) => item.value === value)?.label || value
    );
}

function ruleDirectionSentence(rule: TransactionRule) {
    const parts = [rule.transaction_direction];
    parts.push(rule.transaction_scene ? `场景 ${rule.transaction_scene}` : "不限场景");
    return parts.join(" · ");
}

function ruleRemarkSentence(rule: TransactionRule) {
    return `备注 ${ruleRemarkSummary(rule)}`;
}

function ruleRemarkSummary(rule: TransactionRule) {
    if (rule.match_type === "none") return "不限";
    const matchLabel =
        ruleMatchOptions.find((item) => item.value === rule.match_type)?.label ||
        rule.match_type;
    return `${matchLabel} ${rule.remark_pattern || ""}`.trim();
}

function isEditingRule(rule: TransactionRule) {
    return (
        editingState.value?.kind === "rule" &&
        editingState.value.mode === "edit" &&
        editingState.value.rowKey === ruleKey(rule.id)
    );
}

function startCreateSubject() {
    nodeEditor.value = {
        kind: "subject",
        mode: "create",
        draft: {
            name: "",
        },
    };
}

function startEditSubject(subject: SubjectNode) {
    nodeEditor.value = {
        kind: "subject",
        mode: "edit",
        subjectId: subject.subject.id,
        draft: {
            name: subject.subject.name,
        },
    };
}

function startCreateCategory(subject: SubjectNode) {
    expandedSubjectKeys.value = Array.from(
        new Set([...expandedSubjectKeys.value, subject.key]),
    );
    nodeEditor.value = {
        kind: "category",
        mode: "create",
        parentSubjectId: subject.subject.id,
        draft: {
            name: "",
        },
    };
}

function startEditCategory(category: CategoryNode) {
    nodeEditor.value = {
        kind: "category",
        mode: "edit",
        categoryId: category.category.id,
        draft: {
            name: category.category.name,
        },
    };
}

function startCreateRule(subject: SubjectNode, category: CategoryNode) {
    activeCategoryKey.value = category.key;
    expandedSubjectKeys.value = Array.from(
        new Set([...expandedSubjectKeys.value, subject.key]),
    );
    editingState.value = {
        kind: "rule",
        mode: "create",
        parentKey: category.key,
        draft: {
            subject_id: subject.subject.id,
            category_id: category.category.id,
            platform_code: null,
            transaction_direction: "入账",
            transaction_scene: "",
            match_type: "contains",
            remark_pattern: "",
            result_direction: "original",
            priority: nextRulePriority(category),
            status: 1,
            remark_field: "备注",
            direction_field: "动账方向",
            amount_field: "动账金额",
            remark_exclude_pattern: "",
        },
    };
}

function startEditRule(rule: TransactionRule) {
    editingState.value = {
        kind: "rule",
        mode: "edit",
        rowKey: ruleKey(rule.id),
        ruleId: rule.id,
        draft: {
            subject_id: rule.subject_id,
            category_id: rule.category_id,
            platform_code: rule.platform_code ?? null,
            transaction_direction: rule.transaction_direction,
            transaction_scene: rule.transaction_scene || "",
            match_type: rule.match_type as RuleMatchType,
            remark_pattern: rule.remark_pattern || "",
            result_direction: rule.result_direction,
            priority: rule.priority,
            status: rule.status,
            remark_field: rule.remark_field || "备注",
            direction_field: rule.direction_field || "动账方向",
            amount_field: rule.amount_field || "动账金额",
            remark_exclude_pattern: rule.remark_exclude_pattern || "",
        },
    };
}

function nextSubjectSortOrder() {
    return (
        Math.max(0, ...subjects.value.map((item) => Number(item.sort_order || 0))) +
        10
    );
}

function nextCategorySortOrder(subject: SubjectNode) {
    return (
        Math.max(
            0,
            ...subject.categories.map((item) => Number(item.category.sort_order || 0)),
        ) + 10
    );
}

function nextRulePriority(category: CategoryNode) {
    return (
        Math.max(0, ...categoryContexts.value
            .find((item) => item.category.category.id === category.category.id)
            ?.category.rules.map((item) => Number(item.priority || 0)) ?? [0]) + 10
    );
}

function cancelEditing() {
    editingState.value = null;
}

async function saveNodeEditor() {
    if (!nodeEditor.value) return;
    try {
        if (nodeEditor.value.kind === "subject") {
            const payload = normalizeNameDraft(nodeEditor.value.draft.name, "科目");
            if (nodeEditor.value.mode === "create") {
                await createTransactionSubject({
                    ...payload,
                    sort_order: nextSubjectSortOrder(),
                    status: 1,
                });
                ElMessage.success("科目已新增");
            } else {
                await updateTransactionSubject(nodeEditor.value.subjectId, payload);
                ElMessage.success("科目已更新");
            }
        } else {
            const payload = normalizeNameDraft(nodeEditor.value.draft.name, "重分类");
            if (nodeEditor.value.mode === "create") {
                await createTransactionCategory({
                    subject_id: nodeEditor.value.parentSubjectId,
                    ...payload,
                    sort_order: nextCategorySortOrder(
                        subjectNodes.value.find(
                            (item) => item.subject.id === nodeEditor.value.parentSubjectId,
                        )!,
                    ),
                    status: 1,
                });
                ElMessage.success("重分类已新增");
            } else {
                await updateTransactionCategory(nodeEditor.value.categoryId, payload);
                ElMessage.success("重分类已更新");
            }
        }
    } catch (error) {
        if (error instanceof Error && error.message.endsWith("_required")) {
            return;
        }
        throw error;
    }

    nodeEditor.value = null;
    await loadData({ keepExpansion: true });
}

async function saveEditingRow() {
    if (!editingState.value) return;
    try {
        const payload = normalizeRuleDraft(editingState.value.draft);
        if (editingState.value.mode === "create") {
            await createTransactionRule(payload);
            ElMessage.success("规则已新增");
        } else {
            await updateTransactionRule(editingState.value.ruleId, payload);
            ElMessage.success("规则已更新");
        }
    } catch (error) {
        if (error instanceof Error && error.message.endsWith("_required")) {
            return;
        }
        throw error;
    }

    editingState.value = null;
    await loadData({ keepExpansion: true });
}

function normalizeNameDraft(nameValue: string, label: string) {
    const name = String(nameValue || "").trim();
    if (!name) {
        ElMessage.warning(`请输入${label}名称`);
        throw new Error("name_required");
    }
    return { name };
}

function normalizeRuleDraft(draft: RuleDraft) {
    const transactionDirection = String(draft.transaction_direction || "").trim();
    const matchType = draft.match_type;
    const remarkPattern = String(draft.remark_pattern || "").trim();
    if (!transactionDirection) {
        ElMessage.warning("请选择方向");
        throw new Error("direction_required");
    }
    if (matchType !== "none" && !remarkPattern) {
        ElMessage.warning("请输入备注条件");
        throw new Error("remark_required");
    }
    return {
        subject_id: draft.subject_id,
        category_id: draft.category_id,
        platform_code: draft.platform_code,
        transaction_direction: transactionDirection,
        transaction_scene: normalizeNullableText(draft.transaction_scene),
        match_type: matchType,
        remark_pattern: remarkPattern,
        result_direction: draft.result_direction,
        priority: Number(draft.priority ?? 100),
        status: Number(draft.status ?? 1),
        remark_field: draft.remark_field || "备注",
        direction_field: draft.direction_field || "动账方向",
        amount_field: draft.amount_field || "动账金额",
        remark_exclude_pattern: draft.remark_exclude_pattern || "",
    };
}

function normalizeNullableText(value: string | null | undefined) {
    const text = String(value || "").trim();
    return text || null;
}

async function removeSubject(subject: SubjectNode) {
    await ElMessageBox.confirm(
        `确认删除科目“${subject.subject.name}”吗？`,
        "删除确认",
        {
            type: "warning",
            confirmButtonText: "删除",
            cancelButtonText: "取消",
        },
    );
    await deleteTransactionSubject(subject.subject.id);
    ElMessage.success("科目已删除");
    await loadData({ keepExpansion: true });
}

async function removeCategory(category: CategoryNode) {
    await ElMessageBox.confirm(
        `确认删除重分类“${category.category.name}”吗？`,
        "删除确认",
        {
            type: "warning",
            confirmButtonText: "删除",
            cancelButtonText: "取消",
        },
    );
    await deleteTransactionCategory(category.category.id);
    ElMessage.success("重分类已删除");
    await loadData({ keepExpansion: true });
}

async function removeRule(rule: TransactionRule) {
    await ElMessageBox.confirm(`确认删除规则 #${rule.id} 吗？`, "删除确认", {
        type: "warning",
        confirmButtonText: "删除",
        cancelButtonText: "取消",
    });
    await deleteTransactionRule(rule.id);
    ElMessage.success("规则已删除");
    await loadData({ keepExpansion: true });
}

async function loadPlatformOptions() {
    try {
        const items = await getPlatformList();
        platforms.value = items.length ? items : getFallbackPlatforms();
    } catch {
        platforms.value = getFallbackPlatforms();
    }
}

async function loadData(options: { keepExpansion?: boolean } = {}) {
    loading.value = true;
    try {
        await loadPlatformOptions();
        const [subjectItems, categoryItems, ruleItems] = await Promise.all([
            listTransactionSubjects(),
            listTransactionCategories(),
            listTransactionRules(),
        ]);
        subjects.value = subjectItems;
        categories.value = categoryItems;
        rules.value = ruleItems;
        if (!expansionInitialized.value || !options.keepExpansion) {
            resetExpansionState();
            expansionInitialized.value = true;
        } else {
            syncExpansionState();
        }
    } finally {
        loading.value = false;
    }
}

function resetExpansionState() {
    expandedSubjectKeys.value = [];
}

function syncExpansionState() {
    const subjectKeys = new Set(subjectNodes.value.map((item) => item.key));
    expandedSubjectKeys.value = expandedSubjectKeys.value.filter((key) =>
        subjectKeys.has(key),
    );
}

onMounted(loadData);

usePageRefresh(() => loadData({ keepExpansion: true }));
</script>

<style scoped lang="scss">
@use "./transaction.scss";

.split-rule-page {
    gap: 16px;
}

.rule-toolbar {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
}

.rule-toolbar__actions {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
}

.rule-search-input {
    width: min(320px, 40vw);
}

.rule-summary {
    margin-top: 12px;
    color: var(--text-tertiary);
    font-size: 12px;
}

.rule-workspace {
    display: grid;
    grid-template-columns: minmax(280px, 0.33fr) minmax(0, 1fr);
    gap: 16px;
    min-width: 0;
}

.rule-tree-card,
.rule-detail-card {
    min-width: 0;

    :deep(.el-card__header) {
        display: flex;
        align-items: center;
        min-height: 78px;
        padding: 14px 16px;
    }

    :deep(.el-card__body) {
        padding: 0;
    }
}

.panel-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    min-width: 0;
}

.panel-header__title {
    color: var(--text-primary);
    font-size: 15px;
    font-weight: 700;
}

.panel-header__meta,
.panel-header__count {
    color: var(--text-tertiary);
    font-size: 12px;
}

.rule-tree {
    min-width: 0;
}

.tree-group + .tree-group {
    border-top: 1px solid var(--border-light);
}

.tree-group__children {
    padding: 0 8px 8px 30px;
}

.tree-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
    align-items: center;
    padding: 8px 10px;
    background: var(--bg-card);
}

.tree-row--category {
    margin-top: 2px;
    padding: 0;
    border: 0;
    border-radius: 6px;
}

.tree-row--category.is-active {
    background: color-mix(in srgb, var(--primary) 5%, var(--bg-card));
}

.tree-row__main {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    padding: 0;
    border: 0;
    color: inherit;
    text-align: left;
    background: transparent;
    cursor: pointer;
}

.tree-row__main--category {
    width: 100%;
    padding: 8px 10px;
}

.tree-row__icon {
    display: inline-flex;
    width: 14px;
    justify-content: center;
    color: var(--text-tertiary);
}

.tree-row__copy {
    display: grid;
    gap: 4px;
    min-width: 0;
}

.tree-row__copy strong {
    overflow: hidden;
    color: var(--text-primary);
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.tree-row__copy small {
    color: var(--text-tertiary);
    font-size: 12px;
}

.tree-row__more {
    min-width: 30px;
    padding: 0 6px;
    color: var(--text-tertiary);
    font-size: 16px;
    cursor: pointer;
    border: 0;
    border-radius: 6px;
    background: transparent;
}

.tree-row__more:hover:not(:disabled) {
    color: var(--text-primary);
    background: color-mix(in srgb, var(--primary) 6%, transparent);
}

.tree-row__more:disabled {
    cursor: not-allowed;
    opacity: 0.45;
}

.tree-empty-row {
    padding: 12px;
    color: var(--text-tertiary);
    font-size: 12px;
}

.detail-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    width: 100%;
    min-width: 0;
}

.detail-header__copy {
    display: grid;
    flex: 1;
    gap: 4px;
    min-width: 0;
}

.detail-header__eyebrow {
    overflow: hidden;
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 700;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.detail-header__copy strong {
    overflow: hidden;
    color: var(--text-primary);
    font-size: 16px;
    font-weight: 700;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.detail-header__copy small {
    overflow: hidden;
    color: var(--text-tertiary);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.rule-list {
    min-width: 0;
}

.rule-list__head,
.rule-list__row {
    display: grid;
    grid-template-columns: 120px minmax(0, 1.8fr) 150px 120px 130px;
    gap: 12px;
    align-items: center;
}

.rule-list__head {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-light);
    background: var(--table-header-bg);
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 700;
}

.rule-list__row {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-light);
}

.rule-list__row--editing {
    background: color-mix(in srgb, var(--primary) 3%, var(--bg-card));
}

.rule-list__platform,
.rule-list__amount,
.rule-list__result {
    color: var(--text-secondary);
    font-size: 13px;
}

.rule-summary-text {
    display: grid;
    gap: 4px;
    min-width: 0;
}

.rule-summary-text strong {
    color: var(--text-primary);
    font-size: 13px;
    font-weight: 700;
    line-height: 1.5;
}

.rule-summary-text span {
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.5;
}

.rule-list__actions {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 6px;
}

.rule-detail-empty {
    padding: 32px 0;
}

.rule-editor {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px 8px;
    width: 100%;
    font-size: 12px;
}

.rule-editor > span {
    color: var(--text-tertiary);
    white-space: nowrap;
}

.rule-editor__field {
    flex: 0 0 auto;
}

.rule-editor__field--xs {
    width: 88px;
}

.rule-editor__field--sm {
    width: 144px;
}

.rule-editor__field--md {
    width: 150px;
}

.node-dialog {
    display: grid;
    gap: 10px;
}

.node-dialog__tip {
    margin: 0;
    color: var(--text-tertiary);
    font-size: 12px;
    line-height: 1.5;
}

@media (max-width: 1180px) {
    .rule-workspace {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 900px) {
    .rule-tree-card,
    .rule-detail-card {
        :deep(.el-card__header) {
            min-height: auto;
        }
    }

    .rule-toolbar {
        flex-direction: column;
    }

    .rule-toolbar__actions,
    .rule-search-input {
        width: 100%;
    }

    .detail-header,
    .panel-header {
        flex-direction: column;
        align-items: flex-start;
    }

    .rule-list__head {
        display: none;
    }

    .rule-list__row {
        grid-template-columns: 1fr;
        gap: 10px;
    }

    .rule-list__actions {
        justify-content: flex-start;
    }
}
</style>
