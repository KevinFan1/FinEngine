<template>
    <div class="page-container major-category-page">
        <el-card shadow="never" class="search-card">
            <div class="major-toolbar">
                <SearchCardIntro
                    kicker="MAJOR CATEGORY"
                    title="资金大分类"
                    tip="在这里维护大分类本身，并直接勾选科目归属"
                />
                <div class="major-toolbar__actions">
                    <el-input
                        v-model="searchText"
                        clearable
                        class="major-search-input"
                        placeholder="搜索大分类或已关联科目"
                    >
                        <template #prefix>
                            <el-icon><Search /></el-icon>
                        </template>
                    </el-input>
                    <el-button @click="loadData">
                        <el-icon><Refresh /></el-icon>
                        刷新
                    </el-button>
                    <el-button
                        type="primary"
                        :disabled="drawerVisible"
                        @click="startCreate"
                    >
                        <el-icon><Plus /></el-icon>
                        新增大分类
                    </el-button>
                </div>
            </div>

            <div class="overview-strip">
                <article class="overview-item">
                    <span>大分类</span>
                    <strong>{{ rows.length }}</strong>
                    <small>独立主数据</small>
                </article>
                <article class="overview-item">
                    <span>已关联科目</span>
                    <strong>{{ assignedSubjectCount }}</strong>
                    <small>通过本页维护归属</small>
                </article>
                <article class="overview-item">
                    <span>未分配科目</span>
                    <strong>{{ unassignedSubjects.length }}</strong>
                    <small>可直接拖回任一大分类</small>
                </article>
                <article class="overview-item">
                    <span>停用分类</span>
                    <strong>{{ disabledCategoryCount }}</strong>
                    <small>不会影响历史快照</small>
                </article>
            </div>
        </el-card>

        <el-card shadow="never" class="table-card major-table-card">
            <template #header>
                <div class="card-header">
                    <div class="summary-title-group">
                        <span class="card-header-title">大分类列表</span>
                        <span class="summary-count">
                            共 {{ filteredRows.length }} 条
                        </span>
                    </div>
                </div>
            </template>

            <div v-loading="loading" class="major-grid">
                <div class="major-grid__head">
                    <span>名称</span>
                    <span>状态</span>
                    <span>排序</span>
                    <span>关联科目</span>
                    <span>更新时间</span>
                    <span>操作</span>
                </div>

                <template v-for="row in filteredRows" :key="row.id">
                    <div class="major-grid__row">
                        <div class="major-grid__cell major-grid__cell--title">
                            <strong>{{ row.name }}</strong>
                        </div>
                        <div class="major-grid__cell">
                            <el-tag
                                :type="row.status === 1 ? 'success' : 'info'"
                                size="small"
                            >
                                {{ row.status === 1 ? "启用" : "停用" }}
                            </el-tag>
                        </div>
                        <div class="major-grid__cell">
                            {{ row.sort_order }}
                        </div>
                        <div class="major-grid__cell">
                            <div class="subject-preview">
                                <el-tag
                                    v-for="subject in previewSubjects(row.id)"
                                    :key="subject.id"
                                    size="small"
                                    effect="plain"
                                    :type="accountTypeTagType(subject.account_type)"
                                >
                                    {{ subject.account_type }} · {{ subject.name }}
                                </el-tag>
                                <span
                                    v-if="subjectOverflowCount(row.id) > 0"
                                    class="subject-preview__more"
                                >
                                    +{{ subjectOverflowCount(row.id) }}
                                </span>
                                <span
                                    v-if="!subjectCountByMajor.get(row.id)"
                                    class="major-grid__cell--muted"
                                >
                                    暂无科目
                                </span>
                            </div>
                        </div>
                        <div class="major-grid__cell major-grid__cell--muted">
                            {{ formatDateTime(row.updated_at) }}
                        </div>
                        <div class="major-grid__cell major-grid__cell--actions">
                            <el-button
                                type="primary"
                                link
                                :disabled="drawerVisible"
                                @click="startEdit(row)"
                            >
                                编辑
                            </el-button>
                            <el-button
                                type="danger"
                                link
                                :disabled="drawerVisible"
                                @click="removeRow(row)"
                            >
                                删除
                            </el-button>
                        </div>
                    </div>
                </template>

                <el-empty
                    v-if="!loading && !filteredRows.length"
                    :description="
                        searchText.trim() ? '没有匹配到大分类' : '暂无资金大分类'
                    "
                    :image-size="80"
                />
            </div>
        </el-card>

        <el-drawer
            v-model="drawerVisible"
            :title="drawerTitle"
            size="860px"
            class="major-category-drawer"
            append-to-body
            destroy-on-close
            :close-on-click-modal="false"
            @closed="resetDrawer"
        >
            <el-form label-position="top" class="major-drawer-form">
                <section class="drawer-section">
                    <div class="drawer-section__head">
                        <div>
                            <strong>基础信息</strong>
                            <span>维护大分类本身的名称、状态和排序</span>
                        </div>
                    </div>

                    <div class="major-form-grid">
                        <el-form-item label="大分类名称" required>
                            <el-input
                                v-model="drawerForm.name"
                                maxlength="100"
                                show-word-limit
                                placeholder="输入大分类名称"
                            />
                        </el-form-item>
                        <el-form-item label="状态">
                            <el-radio-group v-model="drawerForm.status">
                                <el-radio-button :label="1">启用</el-radio-button>
                                <el-radio-button :label="0">停用</el-radio-button>
                            </el-radio-group>
                        </el-form-item>
                        <el-form-item label="排序">
                            <el-input-number
                                v-model="drawerForm.sort_order"
                                :min="0"
                                :controls="false"
                                style="width: 100%"
                            />
                        </el-form-item>
                    </div>
                </section>

                <section class="drawer-section">
                    <div class="drawer-section__head">
                        <div>
                            <strong>关联科目</strong>
                            <span>参考重分类字典的工作区方式，直接在抽屉里维护归属</span>
                        </div>
                        <span class="drawer-section__meta">
                            已选 {{ drawerSelectedSubjects.length }} 个
                        </span>
                    </div>

                    <div class="subject-transfer">
                        <section class="subject-transfer__panel">
                            <div class="subject-transfer__search">
                                <el-input
                                    v-model="availableSubjectSearch"
                                    clearable
                                    placeholder="过滤"
                                >
                                    <template #prefix>
                                        <el-icon><Search /></el-icon>
                                    </template>
                                </el-input>
                            </div>
                            <div class="subject-transfer__list">
                                <button
                                    v-for="subject in availableTransferSubjects"
                                    :key="subject.id"
                                    type="button"
                                    class="subject-transfer__item"
                                    :class="{
                                        'is-active': activeAvailableSubjectIds.includes(subject.id),
                                    }"
                                    @click="toggleTransferSelection('available', subject.id)"
                                    @dblclick="moveAvailableSubjects([subject.id])"
                                >
                                    <span class="subject-transfer__item-main">
                                        <el-tag
                                            size="small"
                                            effect="plain"
                                            :type="accountTypeTagType(subject.account_type)"
                                        >
                                            {{ subject.account_type }}
                                        </el-tag>
                                        <strong>{{ subject.name }}</strong>
                                    </span>
                                    <small
                                        v-if="subject.major_category_name && !isDrawerSubjectSelected(subject.id)"
                                    >
                                        {{ subject.major_category_name }}
                                    </small>
                                </button>
                                <div
                                    v-if="!availableTransferSubjects.length"
                                    class="subject-transfer__empty"
                                >
                                    暂无可选科目
                                </div>
                            </div>
                        </section>

                        <div class="subject-transfer__actions">
                            <button
                                type="button"
                                class="subject-transfer__arrow"
                                :disabled="!activeAvailableSubjectIds.length"
                                @click="moveAvailableSubjects()"
                            >
                                <span class="subject-transfer__arrow-text">›</span>
                            </button>
                            <button
                                type="button"
                                class="subject-transfer__arrow"
                                :disabled="!activeSelectedSubjectIds.length"
                                @click="moveSelectedSubjects()"
                            >
                                <span class="subject-transfer__arrow-text">‹</span>
                            </button>
                        </div>

                        <section class="subject-transfer__panel">
                            <div class="subject-transfer__search">
                                <el-input
                                    v-model="selectedSubjectSearch"
                                    clearable
                                    placeholder="过滤"
                                >
                                    <template #prefix>
                                        <el-icon><Search /></el-icon>
                                    </template>
                                </el-input>
                            </div>
                            <div class="subject-transfer__list">
                                <button
                                    v-for="subject in selectedTransferSubjects"
                                    :key="subject.id"
                                    type="button"
                                    class="subject-transfer__item"
                                    :class="{
                                        'is-active': activeSelectedSubjectIds.includes(subject.id),
                                    }"
                                    @click="toggleTransferSelection('selected', subject.id)"
                                    @dblclick="moveSelectedSubjects([subject.id])"
                                >
                                    <span class="subject-transfer__item-main">
                                        <el-tag
                                            size="small"
                                            effect="plain"
                                            :type="accountTypeTagType(subject.account_type)"
                                        >
                                            {{ subject.account_type }}
                                        </el-tag>
                                        <strong>{{ subject.name }}</strong>
                                    </span>
                                    <small
                                        v-if="subject.major_category_name && !isDrawerSubjectSelected(subject.id)"
                                    >
                                        {{ subject.major_category_name }}
                                    </small>
                                </button>
                                <div
                                    v-if="!selectedTransferSubjects.length"
                                    class="subject-transfer__empty"
                                >
                                    暂无已选科目
                                </div>
                            </div>
                        </section>
                    </div>

                    <div class="form-tip">
                        左侧是待选科目，右侧是当前大分类已关联科目。双击条目也可以直接移动；如果选择了其他大分类下的科目，保存后会自动改归到当前大分类。
                    </div>
                </section>
            </el-form>

            <div class="drawer-footer">
                <el-button @click="drawerVisible = false">取消</el-button>
                <el-button
                    type="primary"
                    :loading="drawerSaving"
                    @click="saveDrawer"
                >
                    确定
                </el-button>
            </div>
        </el-drawer>
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "TransactionMajorCategories" });

import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
    createTransactionMajorCategory,
    deleteTransactionMajorCategory,
    listTransactionMajorCategories,
    listTransactionSubjects,
    updateTransactionMajorCategory,
    updateTransactionSubject,
    type TransactionMajorCategory,
    type TransactionSubject,
} from "@/api/transactionAccounting";
import SearchCardIntro from "@/components/SearchCardIntro.vue";
import { usePageRefresh } from "@/composables/pageRefresh";
import { formatDateTime } from "@/utils/format";

type DrawerMode = "create" | "edit";

const loading = ref(false);
const drawerSaving = ref(false);
const rows = ref<TransactionMajorCategory[]>([]);
const subjects = ref<TransactionSubject[]>([]);
const searchText = ref("");
const drawerVisible = ref(false);
const drawerMode = ref<DrawerMode>("create");
const drawerEditId = ref<number | null>(null);
const drawerSubjectIds = ref<number[]>([]);
const drawerInitialSubjectIds = ref<number[]>([]);
const availableSubjectSearch = ref("");
const selectedSubjectSearch = ref("");
const activeAvailableSubjectIds = ref<number[]>([]);
const activeSelectedSubjectIds = ref<number[]>([]);
const drawerForm = reactive({
    name: "",
    sort_order: 0,
    status: 1,
});

const subjectOptions = computed(() =>
    subjects.value
        .slice()
        .sort(
            (left, right) =>
                Number(left.sort_order || 0) - Number(right.sort_order || 0) ||
                left.id - right.id,
        ),
);

const subjectCountByMajor = computed(() => {
    const map = new Map<number, number>();
    subjects.value.forEach((subject) => {
        if (!subject.major_category_id) return;
        map.set(
            subject.major_category_id,
            (map.get(subject.major_category_id) || 0) + 1,
        );
    });
    return map;
});

const assignedSubjectCount = computed(
    () => subjects.value.filter((item) => item.major_category_id).length,
);
const unassignedSubjects = computed(() =>
    subjects.value.filter((item) => !item.major_category_id),
);
const disabledCategoryCount = computed(
    () => rows.value.filter((item) => item.status !== 1).length,
);

const filteredRows = computed(() => {
    const keyword = searchText.value.trim().toLowerCase();
    if (!keyword) return rows.value;
    return rows.value.filter((row) => {
        if (row.name.toLowerCase().includes(keyword)) return true;
        return subjects.value.some(
            (subject) =>
                subject.major_category_id === row.id &&
                subject.name.toLowerCase().includes(keyword),
        );
    });
});

const drawerTitle = computed(() =>
    drawerMode.value === "create" ? "新增资金大分类" : "编辑资金大分类",
);
const drawerSelectedSubjects = computed(() => {
    const selected = new Set(drawerSubjectIds.value);
    return subjectOptions.value.filter((subject) => selected.has(subject.id));
});
const availableTransferSubjects = computed(() => {
    const selected = new Set(drawerSubjectIds.value);
    return subjectOptions.value.filter(
        (subject) =>
            !selected.has(subject.id) &&
            matchesSubjectKeyword(subject, availableSubjectSearch.value),
    );
});
const selectedTransferSubjects = computed(() => {
    const selected = new Set(drawerSubjectIds.value);
    return subjectOptions.value.filter(
        (subject) =>
            selected.has(subject.id) &&
            matchesSubjectKeyword(subject, selectedSubjectSearch.value),
    );
});

async function loadData() {
    loading.value = true;
    try {
        const [majorCategoryItems, subjectItems] = await Promise.all([
            listTransactionMajorCategories(),
            listTransactionSubjects(),
        ]);
        rows.value = majorCategoryItems;
        subjects.value = subjectItems;
    } finally {
        loading.value = false;
    }
}

function startCreate() {
    drawerMode.value = "create";
    drawerEditId.value = null;
    drawerForm.name = "";
    drawerForm.sort_order = nextSortOrder();
    drawerForm.status = 1;
    drawerSubjectIds.value = [];
    drawerInitialSubjectIds.value = [];
    availableSubjectSearch.value = "";
    selectedSubjectSearch.value = "";
    activeAvailableSubjectIds.value = [];
    activeSelectedSubjectIds.value = [];
    drawerVisible.value = true;
}

function startEdit(row: TransactionMajorCategory) {
    drawerMode.value = "edit";
    drawerEditId.value = row.id;
    drawerForm.name = row.name;
    drawerForm.sort_order = row.sort_order;
    drawerForm.status = row.status;
    drawerSubjectIds.value = subjects.value
        .filter((subject) => subject.major_category_id === row.id)
        .map((subject) => subject.id);
    drawerInitialSubjectIds.value = [...drawerSubjectIds.value];
    availableSubjectSearch.value = "";
    selectedSubjectSearch.value = "";
    activeAvailableSubjectIds.value = [];
    activeSelectedSubjectIds.value = [];
    drawerVisible.value = true;
}

async function removeRow(row: TransactionMajorCategory) {
    await ElMessageBox.confirm(`确认删除大分类“${row.name}”吗？`, "删除确认", {
        type: "warning",
        confirmButtonText: "删除",
        cancelButtonText: "取消",
    });
    await deleteTransactionMajorCategory(row.id);
    ElMessage.success("资金大分类已删除");
    await loadData();
}

async function saveDrawer() {
    const name = String(drawerForm.name || "").trim();
    if (!name) {
        ElMessage.warning("请输入大分类名称");
        return;
    }

    const payload = {
        name,
        sort_order: Number(drawerForm.sort_order ?? 100),
        status: Number(drawerForm.status ?? 1),
    };

    drawerSaving.value = true;
    try {
        let majorCategoryId = drawerEditId.value;
        if (drawerMode.value === "create") {
            const created = await createTransactionMajorCategory(payload);
            majorCategoryId = created.id;
        } else if (majorCategoryId) {
            await updateTransactionMajorCategory(majorCategoryId, payload);
        }

        if (majorCategoryId) {
            await saveSubjectAssignments(majorCategoryId);
        }

        ElMessage.success(
            drawerMode.value === "create"
                ? "资金大分类已新增"
                : "资金大分类已更新",
        );
        drawerVisible.value = false;
        await loadData();
    } finally {
        drawerSaving.value = false;
    }
}

async function saveSubjectAssignments(majorCategoryId: number) {
    const selectedIds = new Set(drawerSubjectIds.value);
    const currentIds = new Set(drawerInitialSubjectIds.value);
    const toAssign = Array.from(selectedIds).filter((subjectId) => {
        const subject = subjects.value.find((item) => item.id === subjectId);
        return subject?.major_category_id !== majorCategoryId;
    });
    const toRemove = Array.from(currentIds).filter(
        (subjectId) => !selectedIds.has(subjectId),
    );
    if (!toAssign.length && !toRemove.length) return;

    await Promise.all([
        ...toAssign.map((subjectId) =>
            updateTransactionSubject(subjectId, {
                major_category_id: majorCategoryId,
            }),
        ),
        ...toRemove.map((subjectId) =>
            updateTransactionSubject(subjectId, {
                major_category_id: null,
            }),
        ),
    ]);
}

function resetDrawer() {
    drawerMode.value = "create";
    drawerEditId.value = null;
    drawerForm.name = "";
    drawerForm.sort_order = 0;
    drawerForm.status = 1;
    drawerSubjectIds.value = [];
    drawerInitialSubjectIds.value = [];
    availableSubjectSearch.value = "";
    selectedSubjectSearch.value = "";
    activeAvailableSubjectIds.value = [];
    activeSelectedSubjectIds.value = [];
}

function nextSortOrder() {
    return Math.max(0, ...rows.value.map((row) => row.sort_order || 0)) + 10;
}

function previewSubjects(majorCategoryId: number) {
    return subjects.value
        .filter((subject) => subject.major_category_id === majorCategoryId)
        .slice(0, 3);
}

function subjectOverflowCount(majorCategoryId: number) {
    return Math.max(
        0,
        subjects.value.filter((subject) => subject.major_category_id === majorCategoryId)
            .length - 3,
    );
}

function matchesSubjectKeyword(subject: TransactionSubject, keywordValue: string) {
    const keyword = keywordValue.trim().toLowerCase();
    if (!keyword) return true;
    return [
        subject.account_type,
        subject.name,
        subject.cash_flow_item_name,
        subject.major_category_name,
    ].some((value) => String(value || "").toLowerCase().includes(keyword));
}

function toggleTransferSelection(
    side: "available" | "selected",
    subjectId: number,
) {
    const target =
        side === "available" ? activeAvailableSubjectIds : activeSelectedSubjectIds;
    target.value = target.value.includes(subjectId)
        ? target.value.filter((id) => id !== subjectId)
        : [...target.value, subjectId];
}

function moveAvailableSubjects(subjectIds = activeAvailableSubjectIds.value) {
    const nextIds = subjectIds.filter(
        (subjectId) => !drawerSubjectIds.value.includes(subjectId),
    );
    if (!nextIds.length) return;
    drawerSubjectIds.value = [...drawerSubjectIds.value, ...nextIds];
    activeAvailableSubjectIds.value = activeAvailableSubjectIds.value.filter(
        (subjectId) => !nextIds.includes(subjectId),
    );
    activeSelectedSubjectIds.value = nextIds;
}

function moveSelectedSubjects(subjectIds = activeSelectedSubjectIds.value) {
    if (!subjectIds.length) return;
    const removing = new Set(subjectIds);
    drawerSubjectIds.value = drawerSubjectIds.value.filter(
        (subjectId) => !removing.has(subjectId),
    );
    activeSelectedSubjectIds.value = activeSelectedSubjectIds.value.filter(
        (subjectId) => !removing.has(subjectId),
    );
    activeAvailableSubjectIds.value = subjectIds;
}

function isDrawerSubjectSelected(subjectId: number) {
    return drawerSubjectIds.value.includes(subjectId);
}

function accountTypeTagType(accountType?: string | null) {
    return accountType === "动账账户" ? "warning" : "info";
}

onMounted(loadData);

usePageRefresh(loadData);
</script>

<style scoped lang="scss">
.major-category-page {
    display: grid;
    gap: 16px;
}

.major-toolbar {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
}

.major-toolbar__actions {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
}

.major-search-input {
    width: min(340px, 42vw);
}

.overview-strip {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0;
    margin-top: 16px;
    border-top: 1px solid var(--border-light);
}

.overview-item {
    display: grid;
    gap: 4px;
    min-width: 0;
    padding: 12px 14px 0;
    border-left: 1px solid var(--border-color-light);

    &:first-child {
        padding-left: 0;
        border-left: 0;
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
        line-height: 1.1;
    }

    small {
        color: var(--text-tertiary);
        font-size: 12px;
        line-height: 1.45;
    }
}

.major-table-card {
    :deep(.el-card__body) {
        padding: 0;
    }
}

.major-grid {
    min-width: 0;
}

.major-grid__head,
.major-grid__row {
    display: grid;
    grid-template-columns:
        minmax(200px, 1.1fr)
        110px
        90px
        minmax(260px, 1.45fr)
        180px
        160px;
    gap: 12px;
    align-items: center;
}

.major-grid__head {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-light);
    background: var(--table-header-bg);
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 700;
}

.major-grid__row {
    padding: 14px 16px;
    border-bottom: 1px solid var(--border-light);
}

.major-grid__cell {
    min-width: 0;
    color: var(--text-primary);
    font-size: 13px;
}

.major-grid__cell--title strong {
    font-size: 14px;
    line-height: 1.4;
}

.major-grid__cell--muted {
    color: var(--text-tertiary);
}

.major-grid__cell--actions {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 6px;
}

.subject-preview {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
}

.subject-preview__more {
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 600;
}

.major-drawer-form {
    display: grid;
    gap: 16px;
}

.drawer-section {
    display: grid;
    gap: 8px;
}

.drawer-section {
    padding: 14px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);
}

.drawer-section__head {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: end;
    gap: 12px;
}

.drawer-section__head strong {
    color: var(--text-primary);
    font-size: 14px;
    font-weight: 700;
}

.drawer-section__head span,
.drawer-section__meta {
    color: var(--text-tertiary);
    font-size: 12px;
}

.drawer-section__meta {
    font-weight: 700;
}

.form-tip {
    margin-top: 6px;
    color: var(--text-tertiary);
    font-size: 12px;
    line-height: 1.5;
}

.major-form-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px 16px;
}

.major-form-grid :deep(.el-form-item:first-child) {
    grid-column: 1 / -1;
}

.subject-transfer {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 44px minmax(0, 1fr);
    gap: 20px;
    align-items: center;
}

.subject-transfer__panel {
    min-width: 0;
    overflow: hidden;
    border: 1px solid var(--border-color-light);
    border-radius: 10px;
    background: var(--bg-card);
}

.subject-transfer__search {
    padding: 14px 14px 10px;
    border-bottom: 1px solid var(--border-light);
    background: color-mix(in srgb, var(--bg-elevated) 70%, var(--bg-card));
}

.subject-transfer__search :deep(.el-input__wrapper) {
    border-radius: 8px;
}

.subject-transfer__list {
    display: grid;
    align-content: start;
    gap: 2px;
    min-height: 440px;
    max-height: 440px;
    overflow: auto;
    padding: 8px;
}

.subject-transfer__item {
    display: grid;
    gap: 4px;
    width: 100%;
    padding: 7px 10px;
    color: var(--text-primary);
    font-size: 14px;
    line-height: 1.5;
    text-align: left;
    cursor: pointer;
    border: 0;
    border-radius: 6px;
    background: transparent;
    transition: background-color 0.18s ease, color 0.18s ease;
}

.subject-transfer__item-main {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
}

.subject-transfer__item-main strong {
    min-width: 0;
    overflow: hidden;
    font-size: 13px;
    font-weight: 700;
    line-height: 1.4;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.subject-transfer__item small {
    display: block;
    overflow: hidden;
    color: var(--text-tertiary);
    font-size: 12px;
    line-height: 1.35;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.subject-transfer__item:hover {
    background: color-mix(in srgb, var(--primary) 6%, var(--bg-card));
}

.subject-transfer__item.is-active {
    color: var(--primary);
    background: color-mix(in srgb, var(--primary) 10%, var(--bg-card));
}

.subject-transfer__empty {
    padding: 14px 10px;
    color: var(--text-tertiary);
    font-size: 13px;
    line-height: 1.5;
}

.subject-transfer__actions {
    display: grid;
    justify-items: center;
    gap: 12px;
}

.subject-transfer__arrow {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    color: var(--text-secondary);
    cursor: pointer;
    border: 1px solid var(--border-color-light);
    border-radius: 999px;
    background: var(--bg-card);
    transition: border-color 0.18s ease, background-color 0.18s ease, color 0.18s ease;
}

.subject-transfer__arrow:hover:not(:disabled) {
    color: var(--primary);
    border-color: color-mix(in srgb, var(--primary) 32%, var(--border-color-light));
    background: color-mix(in srgb, var(--primary) 8%, var(--bg-card));
}

.subject-transfer__arrow:disabled {
    opacity: 0.45;
    cursor: not-allowed;
}

.subject-transfer__arrow-text {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    line-height: 1;
    transform: translateY(-1px);
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
    .major-grid__head {
        display: none;
    }

    .major-grid__row {
        grid-template-columns: 1fr;
        gap: 10px;
    }

    .major-grid__cell--actions,
    .drawer-footer {
        justify-content: flex-start;
    }

    .major-form-grid,
    .subject-transfer {
        grid-template-columns: 1fr;
    }

    .subject-transfer__actions {
        grid-auto-flow: column;
        justify-content: center;
    }
}

@media (max-width: 960px) {
    .major-toolbar {
        flex-direction: column;
    }

    .major-toolbar__actions,
    .major-search-input {
        width: 100%;
    }

    .overview-strip {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .overview-item {
        padding-left: 0;
        border-left: 0;
    }

    .drawer-section__head {
        grid-template-columns: 1fr;
        align-items: start;
    }

    .subject-transfer__list {
        min-height: 320px;
        max-height: 320px;
    }
}
</style>

<style lang="scss">
.major-category-drawer {
    .el-drawer__body {
        display: flex;
        flex-direction: column;
        overflow: auto;
    }
}
</style>
