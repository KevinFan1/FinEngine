<template>
    <el-popover
        v-if="showQuotaPanel"
        placement="bottom-end"
        trigger="hover"
        :width="300"
        popper-class="quota-popover"
    >
        <template #reference>
            <button
                type="button"
                class="quota-chip"
                :class="quotaToneClass"
                aria-label="查看本月上传额度"
            >
                <span class="quota-chip-icon" aria-hidden="true">
                    <el-icon><Upload /></el-icon>
                </span>
                <span class="quota-chip-copy">
                    <!-- <span class="quota-chip-label">Upload</span> -->
                    <strong>{{ quotaUsageLabel }}</strong>
                </span>
                <span class="quota-chip-percent">{{ quotaPercentLabel }}</span>
                <span class="quota-chip-bar" aria-hidden="true">
                    <i :style="{ width: quotaProgressWidth }"></i>
                </span>
            </button>
        </template>

        <div class="quota-popover-content">
            <div class="quota-popover-head">
                <div>
                    <span>当前组织配额</span>
                    <strong>{{ warningTitle }}</strong>
                </div>
                <el-tag
                    size="small"
                    :type="showWarning ? 'warning' : 'success'"
                >
                    {{ quotaPercentLabel }}
                </el-tag>
            </div>
            <p class="quota-popover-desc">{{ warningDescription }}</p>

            <div class="quota-detail-list">
                <div class="quota-detail-item">
                    <span>每月上传额度</span>
                    <strong>{{ quotaUsageLabel }}</strong>
                </div>
                <div class="quota-detail-item">
                    <span>用户数</span>
                    <strong>{{ userUsageLabel }}</strong>
                </div>
                <div class="quota-detail-item">
                    <span>套餐到期</span>
                    <strong :class="{ 'is-danger': quotaInfo?.is_expired }">
                        {{ expireLabel }}
                    </strong>
                </div>
            </div>
        </div>
    </el-popover>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { Upload } from "@element-plus/icons-vue";
import { getQuota, type QuotaInfo } from "@/api/quota";
import { useUserStore } from "@/stores/user";
import { formatDateTime } from "@/utils/format";

const userStore = useUserStore();

const quotaInfo = ref<QuotaInfo | null>(null);
const loading = ref(false);

const monthlyUpload = computed(
    () => quotaInfo.value?.monthly_upload || quotaInfo.value?.storage || null,
);

const showQuotaPanel = computed(() => {
    if (!quotaInfo.value) return false;
    return userStore.isOrgAdmin || showWarning.value;
});

const quotaPercent = computed(() => {
    const percent = monthlyUpload.value?.usage_percent || 0;
    return Math.max(0, Math.min(100, percent));
});

const quotaProgressWidth = computed(() => `${quotaPercent.value}%`);

const quotaPercentLabel = computed(() => `${quotaPercent.value.toFixed(0)}%`);

const quotaUsageLabel = computed(() => {
    const upload = monthlyUpload.value;
    if (!upload) return "-";
    return `${upload.current_gb.toFixed(2)} / ${upload.max_gb}GB`;
});

const userUsageLabel = computed(() => {
    if (!quotaInfo.value) return "-";
    return `${quotaInfo.value.users.current} / ${quotaInfo.value.users.max}`;
});

const expireLabel = computed(() => {
    if (!quotaInfo.value?.plan_expires_at) return "永久有效";
    return formatDateTime(quotaInfo.value.plan_expires_at);
});

const quotaToneClass = computed(() => {
    const upload = monthlyUpload.value;
    if (
        quotaInfo.value?.is_expired ||
        upload?.is_exceeded ||
        quotaPercent.value >= 100
    ) {
        return "quota-chip--danger";
    }
    if (quotaPercent.value >= 90) {
        return "quota-chip--warning";
    }
    return "quota-chip--normal";
});

const showWarning = computed(() => {
    if (!quotaInfo.value) return false;
    const upload = monthlyUpload.value;

    return (
        quotaInfo.value.is_expired ||
        quotaInfo.value.users.is_exceeded ||
        Boolean(upload?.is_exceeded) ||
        quotaInfo.value.users.usage_percent >= 90 ||
        Boolean(upload && upload.usage_percent >= 90)
    );
});

const warningTitle = computed(() => {
    if (!quotaInfo.value) return "";
    const upload = monthlyUpload.value;

    if (quotaInfo.value.is_expired) {
        return "套餐已过期";
    }

    if (quotaInfo.value.users.is_exceeded) {
        return "用户数已超出配额";
    }

    if (upload?.is_exceeded) {
        return "本月上传额度已超出";
    }

    if (quotaInfo.value.users.usage_percent >= 90) {
        return "用户配额即将用尽";
    }

    if (upload && upload.usage_percent >= 90) {
        return "本月上传额度即将用尽";
    }

    return "当前配额";
});

const warningDescription = computed(() => {
    if (!quotaInfo.value) return "";
    const upload = monthlyUpload.value;

    const messages: string[] = [];

    if (quotaInfo.value.is_expired) {
        messages.push("您的套餐已过期，请联系管理员续费");
    }

    if (quotaInfo.value.users.is_exceeded) {
        messages.push(
            `当前用户数 ${quotaInfo.value.users.current} 已超出配额 ${quotaInfo.value.users.max}`,
        );
    }

    if (upload?.is_exceeded) {
        messages.push(
            `本月已上传 ${upload.current_gb.toFixed(2)}GB，已超出每月上传额度 ${upload.max_gb}GB`,
        );
    }

    if (
        quotaInfo.value.users.usage_percent >= 90 &&
        !quotaInfo.value.users.is_exceeded
    ) {
        messages.push(
            `用户配额使用率 ${quotaInfo.value.users.usage_percent.toFixed(1)}%，即将用尽`,
        );
    }

    if (upload && upload.usage_percent >= 90 && !upload.is_exceeded) {
        messages.push(
            `本月上传额度使用率 ${upload.usage_percent.toFixed(1)}%，即将用尽`,
        );
    }

    if (messages.length > 0) {
        return messages.join("；");
    }

    if (upload) {
        return `本月已上传 ${upload.current_gb.toFixed(2)}GB / ${upload.max_gb}GB，每月上传额度会在上传前自动检查。用户数 ${quotaInfo.value.users.current} / ${quotaInfo.value.users.max}。`;
    }

    return `用户数 ${quotaInfo.value.users.current} / ${quotaInfo.value.users.max}`;
});

async function loadQuota() {
    // 超级管理员没有组织，不需要显示配额警告
    if (!userStore.userInfo || userStore.userInfo.role === "superadmin") {
        return;
    }

    loading.value = true;
    try {
        quotaInfo.value = await getQuota();
    } catch (error) {
        console.error("加载配额信息失败:", error);
    } finally {
        loading.value = false;
    }
}

onMounted(() => {
    loadQuota();
});
</script>

<style scoped lang="scss">
.quota-warning {
    display: none;
}

.quota-chip {
    position: relative;
    width: 196px;
    min-height: 38px;
    display: grid;
    grid-template-columns: 24px minmax(0, 1fr) auto;
    grid-template-rows: 24px 3px;
    align-items: center;
    column-gap: 9px;
    row-gap: 5px;
    padding: 6px 10px 6px 8px;
    border: 1px solid rgba(22, 119, 255, 0.18);
    border-radius: var(--radius-btn);
    background:
        linear-gradient(
            180deg,
            rgba(22, 119, 255, 0.055),
            rgba(82, 196, 26, 0.035)
        ),
        var(--bg-card);
    color: var(--text-primary);
    box-shadow: var(--shadow-sm);
    cursor: pointer;
    overflow: hidden;
    transition:
        border-color 0.16s,
        background-color 0.16s,
        box-shadow 0.16s,
        color 0.16s;

    &:hover {
        border-color: rgba(22, 119, 255, 0.34);
        box-shadow: 0 6px 16px rgba(22, 119, 255, 0.1);
    }

    &:focus-visible {
        outline: none;
        box-shadow: var(--focus-ring);
    }
}

.quota-chip-icon {
    width: 24px;
    height: 24px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 7px;
    background: var(--primary-lighter);
    color: var(--primary);

    .el-icon {
        font-size: 15px;
    }
}

.quota-chip-copy {
    display: grid;
    align-content: center;
    gap: 1px;
    min-width: 0;
    height: 24px;

    strong {
        overflow: hidden;
        color: var(--text-primary);
        font-size: 13px;
        font-weight: 700;
        line-height: 14px;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
}

.quota-chip-label {
    color: var(--text-secondary);
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0;
    line-height: 10px;
    text-transform: uppercase;
}

.quota-chip-percent {
    align-self: center;
    color: var(--el-color-success);
    font-size: 16px;
    font-weight: 800;
    line-height: 20px;
}

.quota-chip-bar {
    grid-column: 2 / -1;
    width: 100%;
    height: 3px;
    border-radius: 999px;
    background: var(--border-light);
    overflow: hidden;

    i {
        display: block;
        height: 100%;
        border-radius: inherit;
        background: var(--el-color-success);
    }
}

.quota-chip--warning {
    border-color: rgba(250, 173, 20, 0.34);
    background:
        linear-gradient(
            180deg,
            rgba(250, 173, 20, 0.09),
            rgba(250, 173, 20, 0.035)
        ),
        var(--bg-card);

    .quota-chip-icon {
        background: var(--warning-light);
        color: var(--el-color-warning);
    }

    .quota-chip-percent {
        color: var(--el-color-warning);
    }

    .quota-chip-bar i {
        background: var(--el-color-warning);
    }
}

.quota-chip--danger {
    border-color: rgba(255, 77, 79, 0.34);
    background:
        linear-gradient(
            180deg,
            rgba(255, 77, 79, 0.09),
            rgba(255, 77, 79, 0.035)
        ),
        var(--bg-card);

    .quota-chip-icon {
        background: var(--error-light);
        color: var(--el-color-danger);
    }

    .quota-chip-percent {
        color: var(--el-color-danger);
    }

    .quota-chip-bar i {
        background: var(--el-color-danger);
    }
}

.quota-popover-content {
    display: grid;
    gap: 12px;
}

.quota-popover-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;

    span {
        display: block;
        margin-bottom: 4px;
        color: var(--text-tertiary);
        font-size: 12px;
        font-weight: 700;
    }

    strong {
        color: var(--text-primary);
        font-size: 15px;
        font-weight: 800;
    }
}

.quota-popover-desc {
    margin: 0;
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.6;
}

.quota-detail-list {
    display: grid;
    gap: 8px;
}

.quota-detail-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 8px 10px;
    border: 1px solid var(--border-light);
    border-radius: 8px;
    background: var(--bg-elevated);

    span {
        color: var(--text-tertiary);
        font-size: 12px;
        font-weight: 600;
    }

    strong {
        color: var(--text-primary);
        font-size: 12px;
        font-weight: 800;
        text-align: right;
    }

    .is-danger {
        color: var(--el-color-danger);
    }
}

@media (max-width: 860px) {
    .quota-chip {
        width: 116px;
        grid-template-columns: 22px minmax(0, 1fr);
        padding-right: 8px;
    }

    .quota-chip-icon {
        width: 22px;
        height: 22px;
    }

    .quota-chip-copy,
    .quota-chip-percent {
        display: none;
    }

    .quota-chip-bar {
        grid-column: 2 / -1;
    }
}
</style>
