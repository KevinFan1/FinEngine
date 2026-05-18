<template>
  <div class="quota-management">
    <section class="detail-card">
      <div class="detail-card-header">
        <span>配额信息</span>
        <el-button
          v-if="isSuperAdmin"
          type="primary"
          link
          size="small"
          @click="openEditDialog"
        >
          编辑配额
        </el-button>
      </div>

      <div v-loading="loading" class="quota-content">
        <div v-if="quotaInfo" class="quota-info">
          <!-- 套餐信息 -->
          <div class="quota-section">
            <div class="section-title">套餐信息</div>
            <div class="info-grid">
              <div class="info-item">
                <span class="label">套餐类型</span>
                <el-tag :type="getPlanTypeTag(quotaInfo.plan_type)" size="small">
                  {{ getPlanTypeName(quotaInfo.plan_type) }}
                </el-tag>
              </div>
              <div class="info-item">
                <span class="label">到期时间</span>
                <span :class="{ 'text-danger': quotaInfo.is_expired }">
                  {{ formatExpireTime(quotaInfo.plan_expires_at) }}
                </span>
              </div>
            </div>
          </div>

          <!-- 用户配额 -->
          <div class="quota-section">
            <div class="section-title">用户配额</div>
            <div class="quota-progress">
              <div class="progress-header">
                <span>{{ quotaInfo.users.current }} / {{ quotaInfo.users.max }} 用户</span>
                <span :class="getUsageClass(quotaInfo.users.usage_percent)">
                  {{ quotaInfo.users.usage_percent.toFixed(1) }}%
                </span>
              </div>
              <el-progress
                :percentage="quotaInfo.users.usage_percent"
                :status="getProgressStatus(quotaInfo.users.usage_percent, quotaInfo.users.is_exceeded)"
                :stroke-width="12"
              />
              <div v-if="quotaInfo.users.is_exceeded" class="warning-text">
                <el-icon><WarningFilled /></el-icon>
                用户数已超出配额限制
              </div>
            </div>
          </div>

          <!-- 每月上传额度 -->
          <div class="quota-section">
            <div class="section-title">
              每月上传额度
              <el-button
                v-if="isSuperAdmin"
                type="primary"
                link
                size="small"
                @click="handleRecalculate"
                :loading="recalculating"
              >
                重新计算
              </el-button>
            </div>
            <div class="quota-progress">
              <div class="progress-header">
                <span>{{ monthlyUpload.current_gb.toFixed(2) }} / {{ monthlyUpload.max_gb }} GB</span>
                <span :class="getUsageClass(monthlyUpload.usage_percent)">
                  {{ monthlyUpload.usage_percent.toFixed(1) }}%
                </span>
              </div>
              <el-progress
                :percentage="monthlyUpload.usage_percent"
                :status="getProgressStatus(monthlyUpload.usage_percent, monthlyUpload.is_exceeded)"
                :stroke-width="12"
              />
              <div class="quota-help-text">
                当前自然月已上传文件大小，上传前会自动校验是否充足。
              </div>
              <div v-if="monthlyUpload.is_exceeded" class="warning-text">
                <el-icon><WarningFilled /></el-icon>
                本月上传额度已超出限制
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 编辑配额对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑配额"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="editForm"
        :rules="formRules"
        label-width="120px"
      >
        <el-form-item label="套餐类型" prop="plan_type">
          <el-select v-model="editForm.plan_type" placeholder="请选择套餐类型">
            <el-option label="免费版" value="free" />
            <el-option label="基础版" value="basic" />
            <el-option label="专业版" value="professional" />
            <el-option label="企业版" value="enterprise" />
          </el-select>
        </el-form-item>

        <el-form-item label="到期时间" prop="plan_expires_at">
          <el-date-picker
            v-model="editForm.plan_expires_at"
            type="datetime"
            placeholder="选择到期时间"
            format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="最大用户数" prop="max_users">
          <el-input-number
            v-model="editForm.max_users"
            :min="1"
            :max="10000"
            :step="1"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="每月上传额度(GB)" prop="max_storage_gb">
          <el-input-number
            v-model="editForm.max_storage_gb"
            :min="1"
            :max="10000"
            :step="1"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveQuota" :loading="saving">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import { WarningFilled } from '@element-plus/icons-vue';
import { getQuota, getOrgQuota, updateQuota, recalculateStorage, type QuotaInfo } from '@/api/quota';
import { formatDateTime } from '@/utils/format';

interface Props {
  orgId?: number;
  isSuperAdmin?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  isSuperAdmin: false,
});

const loading = ref(false);
const recalculating = ref(false);
const saving = ref(false);
const quotaInfo = ref<QuotaInfo | null>(null);
const editDialogVisible = ref(false);
const formRef = ref<FormInstance>();

const editForm = ref<{
  plan_type: string;
  plan_expires_at: Date | string | null;
  max_users: number;
  max_storage_gb: number;
}>({
  plan_type: '',
  plan_expires_at: null,
  max_users: 0,
  max_storage_gb: 0,
});

const formRules: FormRules = {
  plan_type: [{ required: true, message: '请选择套餐类型', trigger: 'change' }],
  max_users: [{ required: true, message: '请输入最大用户数', trigger: 'blur' }],
  max_storage_gb: [{ required: true, message: '请输入每月上传额度', trigger: 'blur' }],
};

const monthlyUpload = computed(() => {
  const empty = {
    current_bytes: 0,
    current_gb: 0,
    max_bytes: 0,
    max_gb: 0,
    usage_percent: 0,
    is_exceeded: false,
  };
  return quotaInfo.value?.monthly_upload || quotaInfo.value?.storage || empty;
});

onMounted(() => {
  loadQuota();
});

async function loadQuota() {
  if (!props.orgId) return;

  loading.value = true;
  try {
    // 超级管理员查看指定组织的配额，普通用户查看自己组织的配额
    if (props.isSuperAdmin) {
      quotaInfo.value = await getOrgQuota(props.orgId);
    } else {
      quotaInfo.value = await getQuota();
    }
  } catch (error) {
    console.error('加载配额信息失败:', error);
  } finally {
    loading.value = false;
  }
}

function getPlanTypeName(type: string): string {
  const names: Record<string, string> = {
    free: '免费版',
    basic: '基础版',
    professional: '专业版',
    enterprise: '企业版',
  };
  return names[type] || type;
}

function getPlanTypeTag(type: string): string {
  const tags: Record<string, string> = {
    free: 'info',
    basic: 'success',
    professional: 'warning',
    enterprise: 'danger',
  };
  return tags[type] || 'info';
}

function formatExpireTime(time: string | null): string {
  if (!time) return '永久有效';
  return formatDateTime(time);
}

function getUsageClass(percent: number): string {
  if (percent >= 90) return 'text-danger';
  if (percent >= 70) return 'text-warning';
  return 'text-success';
}

function getProgressStatus(percent: number, isExceeded: boolean): 'success' | 'warning' | 'exception' {
  if (isExceeded || percent >= 100) return 'exception';
  if (percent >= 90) return 'warning';
  return 'success';
}

function openEditDialog() {
  if (!quotaInfo.value || !props.orgId) return;

  editForm.value = {
    plan_type: quotaInfo.value.plan_type,
    // 将 ISO 字符串转换为 Date 对象，供日期选择器使用
    plan_expires_at: quotaInfo.value.plan_expires_at
      ? new Date(quotaInfo.value.plan_expires_at)
      : null,
    max_users: quotaInfo.value.users.max,
    max_storage_gb: monthlyUpload.value.max_gb,
  };

  editDialogVisible.value = true;
}

async function handleSaveQuota() {
  if (!formRef.value || !props.orgId) return;

  await formRef.value.validate();

  saving.value = true;
  try {
    // 准备提交数据，确保日期格式正确
    const submitData = {
      plan_type: editForm.value.plan_type,
      max_users: editForm.value.max_users,
      max_storage_gb: editForm.value.max_storage_gb,
      // 如果有到期时间，转换为 ISO 格式；否则发送 null
      plan_expires_at: editForm.value.plan_expires_at
        ? new Date(editForm.value.plan_expires_at).toISOString()
        : null,
    };

    await updateQuota(props.orgId, submitData);
    ElMessage.success('配额更新成功');
    editDialogVisible.value = false;
    await loadQuota();
  } catch (error) {
    console.error('更新配额失败:', error);
  } finally {
    saving.value = false;
  }
}

async function handleRecalculate() {
  if (!props.orgId) return;

  try {
    await ElMessageBox.confirm(
      '重新计算将扫描所有文件并更新存储使用量，可能需要一些时间。是否继续？',
      '确认重新计算',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );

    recalculating.value = true;
    await recalculateStorage(props.orgId);
    ElMessage.success('存储使用量已重新计算');
    await loadQuota();
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重新计算失败:', error);
    }
  } finally {
    recalculating.value = false;
  }
}
</script>

<style scoped lang="scss">
.quota-management {
  .detail-card {
    border: 1px solid var(--border-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);
    display: grid;
    gap: 12px;
    padding: 14px;
  }

  .detail-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: var(--text-primary);
    font-size: 13px;
    font-weight: 700;
  }

  .quota-content {
    min-height: 100px;
  }

  .quota-info {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .quota-section {
    .section-title {
      margin-bottom: 12px;
      color: var(--text-secondary);
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;

    .info-item {
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding: 10px;
      border: 1px solid var(--border-color-light);
      border-radius: calc(var(--radius-card) - 2px);
      background: var(--bg-elevated);

      .label {
        color: var(--text-tertiary);
        font-size: 12px;
        font-weight: 600;
      }

      > span:not(.label) {
        color: var(--text-primary);
        font-size: 13px;
        font-weight: 600;
      }
    }
  }

  .quota-progress {
    padding: 12px;
    border: 1px solid var(--border-color-light);
    border-radius: calc(var(--radius-card) - 2px);
    background: var(--bg-elevated);

    .progress-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
      font-size: 13px;
      font-weight: 600;
      color: var(--text-primary);
    }

    .warning-text {
      display: flex;
      align-items: center;
      gap: 4px;
      margin-top: 8px;
      font-size: 12px;
      color: var(--el-color-danger);
    }

    .quota-help-text {
      margin-top: 8px;
      color: var(--text-tertiary);
      font-size: 12px;
      line-height: 1.5;
    }
  }

  .text-success {
    color: var(--el-color-success);
  }

  .text-warning {
    color: var(--el-color-warning);
  }

  .text-danger {
    color: var(--el-color-danger);
  }
}
</style>
