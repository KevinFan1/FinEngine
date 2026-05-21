<template>
    <div class="page-container category-dict-page">
        <el-card shadow="never" class="search-card matcher-card">
            <div class="matcher-layout">
                <section class="matcher-copy" aria-label="分类匹配辅助">
                    <p class="search-card-kicker">CATEGORY MATCH</p>
                    <h2 class="search-card-title">输入备注，快速匹配分类</h2>
                    <div class="matcher-form">
                        <el-select
                            v-model="matcher.platformId"
                            filterable
                            placeholder="选择平台"
                            class="matcher-platform"
                        >
                            <el-option
                                v-for="platform in activePlatformOptions"
                                :key="platform.id"
                                :label="platform.name"
                                :value="platform.id"
                            >
                                <PlatformBadge
                                    :platform="platform.code || platform.name"
                                    show-mark
                                />
                            </el-option>
                        </el-select>
                        <el-select
                            v-model="matcher.typeCode"
                            filterable
                            allow-create
                            default-first-option
                            placeholder="业务类型"
                            class="matcher-type"
                        >
                            <el-option
                                v-for="item in typeCodeOptions"
                                :key="item"
                                :label="item"
                                :value="item"
                            />
                        </el-select>
                        <el-button
                            type="primary"
                            :loading="matching"
                            @click="handleMatch"
                        >
                            <el-icon><Search /></el-icon>
                            匹配
                        </el-button>
                    </div>
                    <el-input
                        v-model="matcher.text"
                        type="textarea"
                        :rows="3"
                        maxlength="500"
                        show-word-limit
                        placeholder="粘贴动账备注，如：仲裁申诉通过打款-订单123"
                        @keyup.ctrl.enter="handleMatch"
                    />
                </section>

                <section
                    class="match-result"
                    :class="{ 'match-result--hit': Boolean(matchResult?.category) }"
                    aria-live="polite"
                >
                    <div class="match-result__head">
                        <span>匹配结果</span>
                        <el-tag
                            v-if="matchResult"
                            :type="matchResult.category ? 'success' : 'info'"
                            size="small"
                        >
                            {{ matchTypeLabel(matchResult.match_type) }}
                        </el-tag>
                    </div>
                    <div class="match-result__main">
                        <strong>{{ matchResult?.category || "未匹配" }}</strong>
                        <span>{{ matchResult?.matched_keyword || "当前文本没有命中字典关键词" }}</span>
                    </div>
                    <dl class="match-result__meta">
                        <div>
                            <dt>中文提取</dt>
                            <dd>{{ matchResult?.chinese_text || canonicalPreview || "-" }}</dd>
                        </div>
                        <div>
                            <dt>字典范围</dt>
                            <dd>{{ selectedPlatformLabel }} / {{ matcher.typeCode || "-" }}</dd>
                        </div>
                    </dl>
                </section>
            </div>
        </el-card>

        <el-card shadow="never" class="search-card dict-filter-card">
            <el-form :model="searchForm" inline>
                <el-form-item label="平台">
                    <el-select
                        v-model="searchForm.platformId"
                        clearable
                        filterable
                        placeholder="全部平台"
                        style="width: 190px"
                    >
                        <el-option
                            v-for="platform in activePlatformOptions"
                            :key="platform.id"
                            :label="platform.name"
                            :value="platform.id"
                        >
                            <PlatformBadge :platform="platform.code || platform.name" />
                        </el-option>
                    </el-select>
                </el-form-item>
                <el-form-item label="业务类型">
                    <el-select
                        v-model="searchForm.typeCode"
                        clearable
                        filterable
                        allow-create
                        default-first-option
                        placeholder="全部类型"
                        style="width: 170px"
                    >
                        <el-option
                            v-for="item in typeCodeOptions"
                            :key="item"
                            :label="item"
                            :value="item"
                        />
                    </el-select>
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="handleSearch">搜索</el-button>
                    <el-button @click="handleReset">重置</el-button>
                </el-form-item>
            </el-form>
            <ActiveFilterTags :tags="activeFilterTags" @remove="removeFilterTag" @clear="handleReset" />
        </el-card>

        <el-card shadow="never" class="table-card dict-table-card">
            <template #header>
                <div class="card-header">
                    <div class="dict-title-group">
                        <span class="card-header-title">重分类字典</span>
                        <span class="dict-count">共 {{ pagination.total }} 条</span>
                    </div>
                    <div class="card-header-actions">
                        <el-button @click="fetchData">
                            <el-icon><Refresh /></el-icon>
                            刷新
                        </el-button>
                        <el-button type="primary" @click="handleAdd">
                            <el-icon><Plus /></el-icon>
                            新增字典
                        </el-button>
                    </div>
                </div>
            </template>

            <el-table
                class="summary-table roomy-table"
                :data="tableData"
                v-loading="loading"
                stripe
                border
                style="width: 100%"
                height="calc(100vh - 430px)"
            >
                <el-table-column label="序号" width="70" align="center">
                    <template #default="{ $index }">
                        {{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}
                    </template>
                </el-table-column>
                <el-table-column label="平台" width="130">
                    <template #default="{ row }">
                        <PlatformBadge :platform="platformById(row.platform_id)?.code || platformById(row.platform_id)?.name || String(row.platform_id)" />
                    </template>
                </el-table-column>
                <el-table-column prop="type_code" label="业务类型" width="120" />
                <el-table-column prop="name" label="字典名称" min-width="180" show-overflow-tooltip />
                <el-table-column label="分类数" width="90" align="right">
                    <template #default="{ row }">{{ categoryCount(row.categories) }}</template>
                </el-table-column>
                <el-table-column label="关键词数" width="100" align="right">
                    <template #default="{ row }">{{ keywordCount(row.categories) }}</template>
                </el-table-column>
                <el-table-column label="关键词预览" min-width="260" show-overflow-tooltip>
                    <template #default="{ row }">
                        <span class="keyword-preview">{{ keywordPreview(row.categories) }}</span>
                    </template>
                </el-table-column>
                <el-table-column prop="status" label="状态" width="90" align="center">
                    <template #default="{ row }">
                        <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
                            {{ row.status === 1 ? "启用" : "禁用" }}
                        </el-tag>
                    </template>
                </el-table-column>
                <el-table-column prop="updated_at" label="更新时间" width="170">
                    <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
                </el-table-column>
                <el-table-column label="操作" width="190" fixed="right" align="center">
                    <template #default="{ row }">
                        <el-button type="primary" link @click="handleView(row)">查看</el-button>
                        <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
                        <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
                    </template>
                </el-table-column>

                <template #empty>
                    <el-empty description="暂无重分类字典" :image-size="80" />
                </template>
            </el-table>

            <div class="pagination-area">
                <el-pagination
                    v-model:current-page="pagination.page"
                    v-model:page-size="pagination.pageSize"
                    :total="pagination.total"
                    :page-sizes="PAGE_SIZE_OPTIONS"
                    :layout="PAGINATION_LAYOUT"
                    background
                    @size-change="fetchData"
                    @current-change="fetchData"
                />
            </div>
        </el-card>

        <el-drawer
            v-model="drawerVisible"
            :title="drawerTitle"
            :size="drawerSize"
            class="category-dict-drawer"
            append-to-body
            destroy-on-close
            :close-on-click-modal="false"
        >
            <div v-if="drawerMode === 'detail' && selectedDict" class="detail-panel">
                <section class="detail-hero-card">
                    <div>
                        <span class="detail-kicker">DICT #{{ selectedDict.id }}</span>
                        <h3>{{ selectedDict.name }}</h3>
                        <p>{{ platformById(selectedDict.platform_id)?.name || selectedDict.platform_id }} / {{ selectedDict.type_code }}</p>
                    </div>
                    <div class="detail-badge-row">
                        <PlatformBadge :platform="platformById(selectedDict.platform_id)?.code || platformById(selectedDict.platform_id)?.name || String(selectedDict.platform_id)" />
                        <el-tag :type="selectedDict.status === 1 ? 'success' : 'danger'" size="small">
                            {{ selectedDict.status === 1 ? "启用" : "禁用" }}
                        </el-tag>
                    </div>
                </section>

                <section class="detail-card">
                    <div class="detail-card-header">
                        <span>分类关键词</span>
                        <span>
                            {{ detailVisibleGroups.length }} / {{ categoryCount(selectedDict.categories) }} 类
                            · {{ detailVisibleKeywordCount }} / {{ keywordCount(selectedDict.categories) }} 词
                        </span>
                    </div>
                    <el-input
                        v-model="detailSearchText"
                        class="detail-search-input"
                        clearable
                        placeholder="快速搜索分类或关键词"
                    >
                        <template #prefix>
                            <el-icon><Search /></el-icon>
                        </template>
                    </el-input>

                    <div v-if="detailVisibleGroups.length" class="category-editor-layout detail-category-layout">
                        <aside class="category-sidebar" aria-label="分类列表">
                            <button
                                v-for="group in detailVisibleGroups"
                                :key="group.category"
                                type="button"
                                class="category-tab"
                                :class="{ 'is-active': detailActiveCategory === group.category }"
                                @click="setDetailActiveCategory(group.category)"
                            >
                                <span>{{ group.category }}</span>
                                <small>{{ group.keywords.length }} 词</small>
                            </button>
                        </aside>

                        <section
                            v-if="detailActiveGroup"
                            class="keyword-workspace detail-keyword-workspace"
                            aria-label="当前分类关键词"
                        >
                            <div class="keyword-workspace__head">
                                <div>
                                    <span>当前分类</span>
                                    <strong>{{ detailActiveGroup.category }}</strong>
                                </div>
                            </div>
                            <div class="keyword-input-grid detail-keyword-grid">
                                <div
                                    v-for="keyword in detailActiveGroup.keywords"
                                    :key="`${detailActiveGroup.category}-${keyword}`"
                                    class="keyword-input-row detail-keyword-row"
                                >
                                    <div class="readonly-keyword">{{ keyword }}</div>
                                    <span aria-hidden="true"></span>
                                </div>
                            </div>
                        </section>
                    </div>

                    <el-empty
                        v-else
                        description="没有匹配的分类或关键词"
                        :image-size="80"
                    />

                    <div class="form-tip">
                        输入分类名或关键词可以快速缩小范围。
                    </div>
                </section>
            </div>

            <el-form
                v-else
                ref="formRef"
                :model="form"
                :rules="rules"
                label-position="top"
                class="dict-edit-form"
            >
                <section class="edit-section">
                    <div class="dict-form-grid">
                        <el-form-item label="平台" prop="platform_id">
                            <el-select v-model="form.platform_id" filterable placeholder="选择平台" style="width: 100%">
                                <el-option
                                    v-for="platform in activePlatformOptions"
                                    :key="platform.id"
                                    :label="platform.name"
                                    :value="platform.id"
                                >
                                    <PlatformBadge :platform="platform.code || platform.name" />
                                </el-option>
                            </el-select>
                        </el-form-item>
                        <el-form-item label="业务类型" prop="type_code">
                            <el-select
                                v-model="form.type_code"
                                filterable
                                allow-create
                                default-first-option
                                placeholder="选择或输入业务类型"
                                style="width: 100%"
                            >
                                <el-option
                                    v-for="item in typeCodeOptions"
                                    :key="item"
                                    :label="item"
                                    :value="item"
                                />
                            </el-select>
                        </el-form-item>
                        <el-form-item label="字典名称" prop="name">
                            <el-input v-model="form.name" maxlength="100" show-word-limit placeholder="例如：抖音动账赔付分类" />
                        </el-form-item>
                        <el-form-item label="状态" prop="status">
                            <el-radio-group v-model="form.status">
                                <el-radio-button :label="1">启用</el-radio-button>
                                <el-radio-button :label="0">禁用</el-radio-button>
                            </el-radio-group>
                        </el-form-item>
                    </div>
                </section>

                <el-form-item
                    label="分类关键词"
                    prop="categoryGroups"
                    class="category-groups-form-item"
                >
                    <div class="category-editor">
                        <div class="category-editor-toolbar">
                            <div>
                                <strong>{{ categoryEditorStats.categories }} 个分类</strong>
                                <span>{{ categoryEditorStats.keywords }} 个关键词</span>
                            </div>
                            <div class="category-editor-actions">
                                <el-input
                                    v-model="editSearchText"
                                    class="edit-search-input"
                                    clearable
                                    placeholder="搜索分类或关键词"
                                >
                                    <template #prefix>
                                        <el-icon><Search /></el-icon>
                                    </template>
                                </el-input>
                                <el-button type="primary" plain @click="addCategoryGroup">
                                    <el-icon><Plus /></el-icon>
                                    添加分类
                                </el-button>
                            </div>
                        </div>

                        <div v-if="editVisibleGroups.length" class="category-editor-layout">
                            <aside class="category-sidebar" aria-label="分类列表">
                                <button
                                    v-for="item in editVisibleGroups"
                                    :key="item.group.key"
                                    type="button"
                                    class="category-tab"
                                    :class="{
                                        'is-active': activeCategoryIndex === item.index,
                                        'is-warning': categoryGroupHasIssue(item.group),
                                    }"
                                    @click="setActiveCategory(item.index)"
                                >
                                    <span>{{ categoryDisplayName(item.group, item.index) }}</span>
                                    <small>{{ editVisibleKeywordCount(item) }} / {{ groupKeywordCount(item.group) }} 词</small>
                                </button>
                            </aside>

                            <section
                                v-if="activeCategoryGroup"
                                class="keyword-workspace"
                                aria-label="当前分类关键词编辑"
                            >
                                <div class="keyword-workspace__head">
                                    <div>
                                        <span>当前分类</span>
                                        <strong>{{ categoryDisplayName(activeCategoryGroup, activeCategoryIndex) }}</strong>
                                    </div>
                                    <el-button
                                        v-if="form.categoryGroups.length > 1"
                                        type="danger"
                                        plain
                                        @click="removeCategoryGroup(activeCategoryIndex)"
                                    >
                                        删除分类
                                    </el-button>
                                </div>

                                <div class="category-name-field">
                                    <label>分类名称</label>
                                    <el-input
                                        v-model="activeCategoryGroup.name"
                                        placeholder="例如：赔付收入"
                                        maxlength="80"
                                        clearable
                                    />
                                </div>

                                <div class="keyword-list-head">
                                    <label>关键词</label>
                                    <el-button @click="addKeyword(activeCategoryIndex)">
                                        <el-icon><Plus /></el-icon>
                                        添加关键词
                                    </el-button>
                                </div>

                                <div class="keyword-input-grid">
                                    <div
                                        v-for="item in editVisibleKeywords"
                                        :key="item.keyword.key"
                                        class="keyword-input-row"
                                    >
                                        <el-input
                                            v-model="item.keyword.value"
                                            placeholder="输入关键词"
                                            maxlength="300"
                                            clearable
                                        />
                                        <el-button
                                            v-if="activeCategoryGroup.keywords.length > 1"
                                            circle
                                            text
                                            type="danger"
                                            aria-label="删除关键词"
                                            @click="removeKeyword(activeCategoryIndex, item.index)"
                                        >
                                            <el-icon><Close /></el-icon>
                                        </el-button>
                                    </div>
                                </div>
                            </section>
                        </div>

                        <el-empty
                            v-else
                            description="没有匹配的分类或关键词"
                            :image-size="80"
                        />
                    </div>
                    <div class="form-tip">
                        左侧选择分类，右侧维护关键词。保存时会自动去掉空值和重复关键词。
                    </div>
                </el-form-item>
            </el-form>

            <div v-if="drawerMode !== 'detail'" class="drawer-footer">
                <el-button @click="drawerVisible = false">取消</el-button>
                <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
            </div>
        </el-drawer>
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "CategoryDicts" });

import { computed, onMounted, reactive, ref, watch } from "vue";
import {
    ElMessage,
    ElMessageBox,
    type FormInstance,
    type FormRules,
} from "element-plus";
import {
    classifyCategoryText,
    createCategoryDict,
    deleteCategoryDict,
    getCategoryDictList,
    type CategoryDict,
    type ClassifyResult,
    updateCategoryDict,
} from "@/api/categoryDict";
import { getPlatformList, type Platform } from "@/api/platform";
import ActiveFilterTags from "@/components/ActiveFilterTags.vue";
import PlatformBadge from "@/components/PlatformBadge.vue";
import type { ActiveFilterTag } from "@/components/activeFilterTags";
import { formatDateTime } from "@/utils/format";
import { getFallbackPlatforms } from "@/utils/platform";
import {
    DEFAULT_PAGE_SIZE,
    PAGE_SIZE_OPTIONS,
    PAGINATION_LAYOUT,
} from "@/utils/pagination";

interface DictFormState {
    platform_id: number | null;
    type_code: string;
    name: string;
    status: number;
    categoryGroups: CategoryGroupForm[];
}

interface KeywordForm {
    key: number;
    value: string;
}

interface CategoryGroupForm {
    key: number;
    name: string;
    keywords: KeywordForm[];
}

interface DetailCategoryGroup {
    category: string;
    keywords: string[];
}

interface VisibleCategoryGroup {
    index: number;
    group: CategoryGroupForm;
    keywordIndexes: number[];
}

const TYPE_CODE_FALLBACKS = ["动账", "gmv", "bic", "运费险", "订单"];
let formKeySeed = 1;

const platforms = ref<Platform[]>([]);
const loading = ref(false);
const tableData = ref<CategoryDict[]>([]);
const matchResult = ref<ClassifyResult | null>(null);
const matching = ref(false);

const searchForm = reactive({
    platformId: undefined as number | undefined,
    typeCode: "",
});

interface DictFilterTag extends ActiveFilterTag {
    key: "platformId" | "typeCode";
}

const matcher = reactive({
    platformId: undefined as number | undefined,
    typeCode: "动账",
    text: "",
});

const pagination = reactive({
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
});

const drawerVisible = ref(false);
const drawerMode = ref<"create" | "edit" | "detail">("create");
const editId = ref<number | null>(null);
const selectedDict = ref<CategoryDict | null>(null);
const formRef = ref<FormInstance>();
const submitting = ref(false);
const activeCategoryIndex = ref(0);
const detailActiveCategory = ref("");
const detailSearchText = ref("");
const editSearchText = ref("");

const form = reactive<DictFormState>({
    platform_id: null,
    type_code: "动账",
    name: "",
    status: 1,
    categoryGroups: [createEmptyCategoryGroup()],
});

const activePlatformOptions = computed(() =>
    platforms.value
        .filter((platform) => platform.status !== 0 && platform.id > 0)
        .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0)),
);

const typeCodeOptions = computed(() => {
    const seen = new Set(TYPE_CODE_FALLBACKS);
    tableData.value.forEach((item) => {
        if (item.type_code) seen.add(item.type_code);
    });
    return Array.from(seen);
});

const activeFilterTags = computed<DictFilterTag[]>(() => {
    const tags: DictFilterTag[] = [];
    if (searchForm.platformId) {
        const platform = platforms.value.find((item) => item.id === searchForm.platformId);
        tags.push({
            key: "platformId",
            label: "平台",
            value: platform?.name || String(searchForm.platformId),
        });
    }
    if (searchForm.typeCode) {
        tags.push({ key: "typeCode", label: "业务类型", value: searchForm.typeCode });
    }
    return tags;
});

const selectedPlatformLabel = computed(() => {
    if (!matcher.platformId) return "-";
    return platformById(matcher.platformId)?.name || String(matcher.platformId);
});

const canonicalPreview = computed(() => canonicalRemark(matcher.text));

const drawerTitle = computed(() => {
    if (drawerMode.value === "detail") return "重分类字典详情";
    return editId.value ? "编辑重分类字典" : "新增重分类字典";
});

const drawerSize = computed(() => "min(1120px, 92vw)");

const activeCategoryGroup = computed(
    () => form.categoryGroups[activeCategoryIndex.value] || null,
);

const categoryEditorStats = computed(() => ({
    categories: form.categoryGroups.length,
    keywords: form.categoryGroups.reduce(
        (total, group) => total + groupKeywordCount(group),
        0,
    ),
}));

const editVisibleGroups = computed<VisibleCategoryGroup[]>(() => {
    const query = editSearchText.value.trim().toLowerCase();

    return form.categoryGroups
        .map((group, index) => {
            const categoryMatched = group.name.trim().toLowerCase().includes(query);
            const keywordIndexes = group.keywords
                .map((keyword, keywordIndex) => ({
                    keyword,
                    keywordIndex,
                }))
                .filter(({ keyword }) =>
                    !query || categoryMatched || keyword.value.toLowerCase().includes(query),
                )
                .map(({ keywordIndex }) => keywordIndex);

            return {
                index,
                group,
                keywordIndexes,
            };
        })
        .filter((item) => !query || item.keywordIndexes.length);
});

const activeVisibleGroup = computed(
    () =>
        editVisibleGroups.value.find(
            (item) => item.index === activeCategoryIndex.value,
        ) || editVisibleGroups.value[0] || null,
);

const editVisibleKeywords = computed(() => {
    if (!activeCategoryGroup.value) return [];
    const visibleIndexes = activeVisibleGroup.value?.keywordIndexes;
    const indexes = visibleIndexes?.length
        ? visibleIndexes
        : activeCategoryGroup.value.keywords.map((_keyword, index) => index);

    return indexes.map((index) => ({
        index,
        keyword: activeCategoryGroup.value!.keywords[index],
    }));
});

watch(editVisibleGroups, (groups) => {
    if (!groups.length) return;
    if (!groups.some((item) => item.index === activeCategoryIndex.value)) {
        activeCategoryIndex.value = groups[0].index;
    }
});

const detailAllGroups = computed<DetailCategoryGroup[]>(() => {
    if (!selectedDict.value?.categories) return [];
    return Object.entries(selectedDict.value.categories).map(([category, keywords]) => ({
        category,
        keywords,
    }));
});

const detailVisibleGroups = computed<DetailCategoryGroup[]>(() => {
    const query = detailSearchText.value.trim().toLowerCase();
    if (!query) return detailAllGroups.value;

    return detailAllGroups.value
        .map((group) => {
            const categoryMatched = group.category.toLowerCase().includes(query);
            const keywords = categoryMatched
                ? group.keywords
                : group.keywords.filter((keyword) =>
                    keyword.toLowerCase().includes(query),
                );
            return {
                category: group.category,
                keywords,
            };
        })
        .filter((group) => group.keywords.length);
});

const detailActiveGroup = computed(() => {
    if (!detailVisibleGroups.value.length) return null;
    return (
        detailVisibleGroups.value.find(
            (group) => group.category === detailActiveCategory.value,
        ) || detailVisibleGroups.value[0]
    );
});

const detailVisibleKeywordCount = computed(() =>
    detailVisibleGroups.value.reduce(
        (total, group) => total + group.keywords.length,
        0,
    ),
);

const rules: FormRules = {
    platform_id: [{ required: true, message: "请选择平台", trigger: "change" }],
    type_code: [{ required: true, message: "请输入业务类型", trigger: "blur" }],
    name: [{ required: true, message: "请输入字典名称", trigger: "blur" }],
    categoryGroups: [
        {
            validator: (_rule, _value, callback) => {
                try {
                    buildCategoriesFromGroups(form.categoryGroups);
                    callback();
                } catch (error) {
                    callback(error as Error);
                }
            },
            trigger: "blur",
        },
    ],
};

function platformById(id: number) {
    return platforms.value.find((platform) => platform.id === id);
}

function categoryCount(categories: Record<string, string[]>) {
    return Object.keys(categories || {}).length;
}

function keywordCount(categories: Record<string, string[]>) {
    return Object.values(categories || {}).reduce(
        (total, keywords) => total + keywords.length,
        0,
    );
}

function keywordPreview(categories: Record<string, string[]>) {
    const entries = Object.entries(categories || {});
    if (!entries.length) return "-";
    return entries
        .slice(0, 3)
        .map(([category, keywords]) => `${category}: ${keywords.slice(0, 3).join("、")}`)
        .join(" / ");
}

function matchTypeLabel(type: string) {
    if (type === "exact") return "精确匹配";
    if (type === "contains") return "包含匹配";
    return "未匹配";
}

function canonicalRemark(value: string) {
    if (!value) return "";
    return Array.from(value.matchAll(/[\u4e00-\u9fff]+/g))
        .map((match) => match[0])
        .join("");
}

function createEmptyKeyword(value = ""): KeywordForm {
    return {
        key: formKeySeed++,
        value,
    };
}

function createEmptyCategoryGroup(
    name = "",
    keywords: string[] = [""],
): CategoryGroupForm {
    return {
        key: formKeySeed++,
        name,
        keywords: keywords.length
            ? keywords.map((keyword) => createEmptyKeyword(keyword))
            : [createEmptyKeyword()],
    };
}

function clampActiveCategoryIndex() {
    if (activeCategoryIndex.value < 0) {
        activeCategoryIndex.value = 0;
        return;
    }
    if (activeCategoryIndex.value >= form.categoryGroups.length) {
        activeCategoryIndex.value = Math.max(form.categoryGroups.length - 1, 0);
    }
}

function addCategoryGroup() {
    const group = createEmptyCategoryGroup();
    form.categoryGroups.push(group);
    activeCategoryIndex.value = form.categoryGroups.length - 1;
}

function removeCategoryGroup(index: number) {
    form.categoryGroups.splice(index, 1);
    if (!form.categoryGroups.length) {
        form.categoryGroups.push(createEmptyCategoryGroup());
    }
    clampActiveCategoryIndex();
}

function addKeyword(groupIndex: number) {
    form.categoryGroups[groupIndex].keywords.push(createEmptyKeyword());
}

function removeKeyword(groupIndex: number, keywordIndex: number) {
    const keywords = form.categoryGroups[groupIndex].keywords;
    keywords.splice(keywordIndex, 1);
    if (!keywords.length) {
        keywords.push(createEmptyKeyword());
    }
}

function setActiveCategory(index: number) {
    activeCategoryIndex.value = index;
}

function editVisibleKeywordCount(item: VisibleCategoryGroup) {
    return item.keywordIndexes.length;
}

function setDetailActiveCategory(category: string) {
    detailActiveCategory.value = category;
}

function groupKeywordCount(group: CategoryGroupForm) {
    return group.keywords.filter((keyword) => keyword.value.trim()).length;
}

function categoryGroupHasIssue(group: CategoryGroupForm) {
    return !group.name.trim() || groupKeywordCount(group) === 0;
}

function categoryDisplayName(group: CategoryGroupForm, index: number) {
    return group.name.trim() || `未命名分类 ${index + 1}`;
}

function buildCategoriesFromGroups(
    groups: CategoryGroupForm[],
): Record<string, string[]> {
    const categories: Record<string, string[]> = {};

    groups.forEach((group, groupIndex) => {
        const categoryName = group.name.trim();
        if (!categoryName) {
            throw new Error(`第 ${groupIndex + 1} 个分类名称不能为空`);
        }
        if (categories[categoryName]) {
            throw new Error(`分类「${categoryName}」重复`);
        }

        const keywords: string[] = [];
        group.keywords.forEach((keyword) => {
            const value = keyword.value.trim();
            if (value && !keywords.includes(value)) {
                keywords.push(value);
            }
        });
        if (!keywords.length) {
            throw new Error(`分类「${categoryName}」至少需要一个关键词`);
        }
        categories[categoryName] = keywords;
    });

    if (!Object.keys(categories).length) {
        throw new Error("至少填写一个分类");
    }
    return categories;
}

function categoriesToGroups(categories: Record<string, string[]>) {
    const entries = Object.entries(categories || {});
    if (!entries.length) return [createEmptyCategoryGroup()];
    return entries.map(([category, keywords]) =>
        createEmptyCategoryGroup(category, keywords),
    );
}

async function fetchPlatformOptions() {
    try {
        const res = await getPlatformList();
        platforms.value = res.length ? res : getFallbackPlatforms();
    } catch {
        platforms.value = getFallbackPlatforms();
    }

    const firstPlatform = activePlatformOptions.value[0];
    if (!matcher.platformId && firstPlatform) matcher.platformId = firstPlatform.id;
}

async function fetchData() {
    loading.value = true;
    try {
        const res = await getCategoryDictList({
            page: pagination.page,
            page_size: pagination.pageSize,
            platform_id: searchForm.platformId,
            type_code: searchForm.typeCode || undefined,
        });
        tableData.value = res.items || [];
        pagination.total = res.total || 0;
    } catch {
        // Error handled by interceptor.
    } finally {
        loading.value = false;
    }
}

function handleSearch() {
    pagination.page = 1;
    fetchData();
}

function handleReset() {
    searchForm.platformId = undefined;
    searchForm.typeCode = "";
    handleSearch();
}

function removeFilterTag(tag: DictFilterTag) {
    if (tag.key === "platformId") {
        searchForm.platformId = undefined;
    } else if (tag.key === "typeCode") {
        searchForm.typeCode = "";
    }
    handleSearch();
}

async function handleMatch() {
    if (!matcher.platformId) {
        ElMessage.warning("请先选择平台");
        return;
    }
    if (!matcher.typeCode) {
        ElMessage.warning("请先选择业务类型");
        return;
    }
    if (!matcher.text.trim()) {
        ElMessage.warning("请输入要匹配的备注文字");
        return;
    }

    matching.value = true;
    try {
        matchResult.value = await classifyCategoryText({
            platform_id: matcher.platformId,
            type_code: matcher.typeCode,
            text: matcher.text,
        });
    } catch {
        // Error handled by interceptor.
    } finally {
        matching.value = false;
    }
}

function resetForm() {
    const firstPlatform = activePlatformOptions.value[0];
    form.platform_id = firstPlatform?.id || null;
    form.type_code = "动账";
    form.name = "";
    form.status = 1;
    form.categoryGroups = [createEmptyCategoryGroup()];
    activeCategoryIndex.value = 0;
    editSearchText.value = "";
    editId.value = null;
    selectedDict.value = null;
}

function handleAdd() {
    drawerMode.value = "create";
    resetForm();
    drawerVisible.value = true;
}

function handleView(row: CategoryDict) {
    drawerMode.value = "detail";
    selectedDict.value = row;
    detailSearchText.value = "";
    detailActiveCategory.value = Object.keys(row.categories || {})[0] || "";
    drawerVisible.value = true;
}

function handleEdit(row: CategoryDict) {
    drawerMode.value = "edit";
    editId.value = row.id;
    selectedDict.value = row;
    form.platform_id = row.platform_id;
    form.type_code = row.type_code;
    form.name = row.name;
    form.status = row.status;
    form.categoryGroups = categoriesToGroups(row.categories);
    activeCategoryIndex.value = 0;
    editSearchText.value = "";
    drawerVisible.value = true;
}

async function handleSubmit() {
    const valid = await formRef.value?.validate().catch(() => false);
    if (!valid || !form.platform_id) return;

    const payload = {
        platform_id: form.platform_id,
        type_code: form.type_code.trim(),
        name: form.name.trim(),
        status: form.status,
        categories: buildCategoriesFromGroups(form.categoryGroups),
    };

    submitting.value = true;
    try {
        if (editId.value) {
            await updateCategoryDict(editId.value, payload);
            ElMessage.success("更新成功");
        } else {
            await createCategoryDict(payload);
            ElMessage.success("创建成功");
        }
        drawerVisible.value = false;
        fetchData();
    } catch {
        // Error handled by interceptor.
    } finally {
        submitting.value = false;
    }
}

async function handleDelete(row: CategoryDict) {
    try {
        await ElMessageBox.confirm(
            `确定要删除重分类字典「${row.name}」吗？此操作不可恢复。`,
            "操作确认",
            {
                type: "warning",
                confirmButtonText: "确定",
                cancelButtonText: "取消",
            },
        );
        await deleteCategoryDict(row.id);
        ElMessage.success("删除成功");
        fetchData();
    } catch {
        // Cancelled or error.
    }
}

onMounted(async () => {
    await fetchPlatformOptions();
    await fetchData();
});
</script>

<style scoped lang="scss">
.category-dict-page {
    display: grid;
    gap: 0;
}

.matcher-card {
    :deep(.el-card__body) {
        padding: 16px 18px;
    }
}

.matcher-layout {
    display: grid;
    grid-template-columns: minmax(0, 1.6fr) minmax(280px, 0.9fr);
    gap: 16px;
    align-items: stretch;
}

.matcher-copy {
    display: grid;
    gap: 10px;
    min-width: 0;
}

.search-card-kicker {
    margin: 0;
    color: var(--primary);
    font-family: "SF Mono", SFMono-Regular, Consolas, monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
}

.search-card-title {
    margin: 0;
    color: var(--text-primary);
    font-size: 18px;
    font-weight: 700;
    line-height: 1.35;
}

.matcher-form {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.matcher-platform {
    width: 190px;
}

.matcher-type {
    width: 140px;
}

.match-result {
    display: grid;
    align-content: space-between;
    gap: 14px;
    min-width: 0;
    padding: 14px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-card);
    background: var(--bg-elevated);
}

.match-result--hit {
    border-color: color-mix(in srgb, var(--success) 34%, var(--border-light));
    background: color-mix(in srgb, var(--success) 8%, var(--bg-elevated));
}

.match-result__head,
.detail-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    color: var(--text-secondary);
    font-size: 13px;
    font-weight: 700;
}

.match-result__main {
    display: grid;
    gap: 6px;

    strong {
        color: var(--text-primary);
        font-size: 24px;
        line-height: 1.2;
    }

    span {
        color: var(--text-secondary);
        word-break: break-all;
    }
}

.match-result__meta {
    display: grid;
    gap: 8px;
    margin: 0;

    div {
        display: grid;
        gap: 3px;
    }

    dt {
        color: var(--text-tertiary);
        font-size: 12px;
        font-weight: 600;
    }

    dd {
        margin: 0;
        color: var(--text-secondary);
        word-break: break-all;
    }
}

.dict-filter-card {
    margin-top: 0;
}

.dict-table-card {
    :deep(.el-card__body) {
        padding: 0;
    }
}

.dict-title-group {
    display: flex;
    align-items: baseline;
    gap: 10px;
    min-width: 0;
}

.dict-count {
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 500;
    white-space: nowrap;
}

.keyword-preview {
    color: var(--text-secondary);
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

.form-tip {
    margin-top: 6px;
    color: var(--text-tertiary);
    font-size: 12px;
    line-height: 1.5;
}

.dict-edit-form {
    display: grid;
    gap: 14px;

    :deep(.el-form-item) {
        margin-bottom: 0;
    }
}

.edit-section {
    padding: 14px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);
}

.dict-form-grid {
    display: grid;
    grid-template-columns: minmax(190px, 1fr) minmax(170px, 0.8fr) minmax(260px, 1.3fr) auto;
    gap: 12px;
    align-items: end;
}

.category-groups-form-item {
    :deep(.el-form-item__content) {
        display: block;
        width: 100%;
        line-height: normal;
    }
}

.category-editor {
    display: grid;
    gap: 12px;
    width: 100%;
}

.category-editor-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 14px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);

    > div:first-child {
        display: flex;
        align-items: baseline;
        gap: 10px;
        min-width: 0;
    }

    strong {
        color: var(--text-primary);
        font-size: 14px;
    }

    span {
        color: var(--text-tertiary);
        font-size: 12px;
    }
}

.category-editor-actions {
    display: flex;
    align-items: center;
    gap: 8px;
}

.edit-search-input {
    width: 260px;
}

.category-editor-layout {
    display: grid;
    grid-template-columns: minmax(220px, 0.34fr) minmax(0, 1fr);
    min-height: 420px;
    overflow: hidden;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);
}

.category-sidebar {
    display: grid;
    align-content: start;
    gap: 6px;
    max-height: calc(100vh - 330px);
    min-height: 420px;
    overflow: auto;
    padding: 10px;
    border-right: 1px solid var(--border-light);
    background: color-mix(in srgb, var(--bg-elevated) 86%, var(--bg-card));
}

.category-tab {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
    align-items: center;
    width: 100%;
    min-height: 40px;
    padding: 9px 10px;
    color: var(--text-secondary);
    text-align: left;
    cursor: pointer;
    border: 1px solid transparent;
    border-radius: 6px;
    background: transparent;
    transition: border-color 0.18s ease, background-color 0.18s ease, color 0.18s ease;

    span {
        overflow: hidden;
        font-size: 13px;
        font-weight: 700;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    small {
        color: var(--text-tertiary);
        font-size: 12px;
        white-space: nowrap;
    }

    &:hover,
    &.is-active {
        color: var(--primary);
        border-color: color-mix(in srgb, var(--primary) 28%, transparent);
        background: color-mix(in srgb, var(--primary) 8%, var(--bg-card));
    }

    &.is-warning:not(.is-active) {
        border-color: color-mix(in srgb, var(--warning) 34%, transparent);
    }
}

.keyword-workspace {
    display: grid;
    align-content: start;
    gap: 14px;
    max-height: calc(100vh - 330px);
    min-height: 420px;
    overflow: auto;
    padding: 16px;
    min-width: 0;
}

.keyword-workspace__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-light);

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
        overflow: hidden;
        color: var(--text-primary);
        font-size: 18px;
        line-height: 1.3;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
}

.category-name-field,
.keyword-list-head {
    display: grid;
    gap: 8px;

    label {
        color: var(--text-secondary);
        font-size: 13px;
        font-weight: 700;
    }
}

.keyword-list-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}

.keyword-input-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 10px;
}

.keyword-input-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 32px;
    gap: 8px;
    align-items: center;
}

.detail-panel {
    display: grid;
    gap: 12px;
}

.detail-hero-card,
.detail-card {
    border: 1px solid var(--border-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);
}

.detail-hero-card {
    display: grid;
    gap: 12px;
    padding: 14px;

    h3 {
        margin: 4px 0;
        color: var(--text-primary);
        font-size: 17px;
        font-weight: 700;
        line-height: 1.4;
    }

    p {
        margin: 0;
        color: var(--text-secondary);
        word-break: break-word;
    }
}

.detail-kicker {
    color: var(--text-tertiary);
    font-family: "SF Mono", SFMono-Regular, Consolas, monospace;
    font-size: 11px;
    font-weight: 700;
}

.detail-badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.detail-card {
    display: grid;
    gap: 12px;
    padding: 14px;
}

.detail-search-input {
    max-width: 420px;
}

.detail-category-layout {
    min-height: 360px;
}

.detail-category-layout .category-sidebar,
.detail-keyword-workspace {
    min-height: 360px;
    max-height: calc(100vh - 390px);
}

.keyword-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.detail-keyword-grid {
    align-content: start;
}

.readonly-keyword {
    min-height: 32px;
    padding: 6px 11px;
    color: var(--text-primary);
    line-height: 1.45;
    word-break: break-all;
    border: 1px solid var(--border-color-light);
    border-radius: 6px;
    background: var(--bg-elevated);
}

@media (max-width: 960px) {
    .matcher-layout {
        grid-template-columns: 1fr;
    }

    .matcher-platform,
    .matcher-type {
        width: 100%;
    }

    .matcher-form {
        :deep(.el-button) {
            width: 100%;
        }
    }

    .dict-form-grid,
    .category-editor-layout {
        grid-template-columns: 1fr;
    }

    .category-sidebar {
        grid-auto-flow: column;
        grid-auto-columns: minmax(160px, 1fr);
        min-height: auto;
        max-height: none;
        overflow-x: auto;
        border-right: 0;
        border-bottom: 1px solid var(--border-light);
    }

    .keyword-workspace {
        min-height: 360px;
        max-height: none;
    }

    .keyword-input-grid {
        grid-template-columns: 1fr;
    }

    .detail-search-input {
        max-width: none;
    }

    .category-editor-toolbar,
    .keyword-workspace__head,
    .keyword-list-head {
        align-items: stretch;
        flex-direction: column;
    }

    .category-editor-actions {
        width: 100%;
        flex-direction: column;
    }

    .edit-search-input {
        width: 100%;
    }

    .category-editor-actions,
    .category-editor-toolbar {
        :deep(.el-button) {
            width: 100%;
        }
    }
}
</style>

<style lang="scss">
.category-dict-drawer {
    .el-drawer__body {
        display: flex;
        flex-direction: column;
        overflow: auto;
    }
}
</style>
