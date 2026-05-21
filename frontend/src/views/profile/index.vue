<template>
  <div class="page-container">
    <el-card shadow="never" class="search-card">
      <SearchCardIntro
        kicker="个人中心"
        title="维护当前账号信息和登录密码"
        tip="姓名、手机号和密码都可以在这里修改"
      />
      <el-alert
        v-if="userStore.userInfo?.must_change_password"
        type="warning"
        :closable="false"
        title="当前账号仍在使用初始密码，请先修改后继续使用。"
        style="margin-top: 16px"
      />
    </el-card>

    <section class="profile-grid">
      <el-card shadow="never" class="table-card">
        <template #header>
          <div class="card-header">
            <span class="card-header-title">基本信息</span>
            <el-tag :type="userStore.userInfo?.must_change_password ? 'warning' : 'success'">
              {{ userStore.userInfo?.must_change_password ? '待修改密码' : '账号正常' }}
            </el-tag>
          </div>
        </template>
        <el-form ref="profileFormRef" :model="profileForm" :rules="profileRules" label-width="90px" class="profile-form">
          <el-form-item label="用户名">
            <el-input :model-value="userStore.userInfo?.username || '-'" disabled />
          </el-form-item>
          <el-form-item label="姓名" prop="display_name">
            <el-input v-model="profileForm.display_name" />
          </el-form-item>
          <el-form-item label="手机号" prop="phone">
            <el-input v-model="profileForm.phone" />
          </el-form-item>
          <el-form-item label="角色">
            <el-input :model-value="roleLabel" disabled />
          </el-form-item>
          <el-form-item label="组织">
            <el-input :model-value="userStore.userInfo?.org_name || '-'" disabled />
          </el-form-item>
          <div class="profile-actions">
            <el-button type="primary" :loading="savingProfile" @click="saveProfile">
              保存信息
            </el-button>
          </div>
        </el-form>
      </el-card>

      <el-card shadow="never" class="table-card">
        <template #header>
          <span class="card-header-title">修改密码</span>
        </template>
        <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="90px" class="profile-form">
          <el-form-item label="当前密码" prop="old_password">
            <el-input v-model="passwordForm.old_password" type="password" show-password />
          </el-form-item>
          <el-form-item label="新密码" prop="new_password">
            <el-input v-model="passwordForm.new_password" type="password" show-password />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirm_password">
            <el-input v-model="passwordForm.confirm_password" type="password" show-password />
          </el-form-item>
          <div class="profile-actions">
            <el-button type="primary" :loading="savingPassword" @click="savePassword">
              修改密码
            </el-button>
          </div>
        </el-form>
      </el-card>
    </section>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: "ProfileCenter" });

import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, type FormInstance, type FormRules } from "element-plus";
import { changeMyPassword, getUserInfo, updateMyProfile } from "@/api/auth";
import SearchCardIntro from "@/components/SearchCardIntro.vue";
import { useUserStore } from "@/stores/user";
import { getRoleLabel } from "@/utils/format";

const userStore = useUserStore();
const roleLabel = computed(() => getRoleLabel(userStore.userRole));

const profileFormRef = ref<FormInstance>();
const passwordFormRef = ref<FormInstance>();
const savingProfile = ref(false);
const savingPassword = ref(false);

const profileForm = reactive({
  display_name: "",
  phone: "",
});

const passwordForm = reactive({
  old_password: "",
  new_password: "",
  confirm_password: "",
});

const profileRules: FormRules = {
  display_name: [{ required: true, message: "请输入姓名", trigger: "blur" }],
  phone: [{ required: true, message: "请输入手机号", trigger: "blur" }],
};

const passwordRules: FormRules = {
  old_password: [{ required: true, message: "请输入当前密码", trigger: "blur" }],
  new_password: [{ required: true, message: "请输入新密码", trigger: "blur" }],
  confirm_password: [
    { required: true, message: "请再次输入新密码", trigger: "blur" },
    {
      validator: (_rule, value, callback) => {
        if (value !== passwordForm.new_password) {
          callback(new Error("两次输入的新密码不一致"));
          return;
        }
        callback();
      },
      trigger: "blur",
    },
  ],
};

function syncFromStore() {
  profileForm.display_name = userStore.userInfo?.display_name || "";
  profileForm.phone = userStore.userInfo?.phone || "";
}

async function refreshUser() {
  const info = await getUserInfo();
  userStore.setUserInfo(info as any);
  syncFromStore();
}

async function saveProfile() {
  await profileFormRef.value?.validate();
  savingProfile.value = true;
  try {
    const info = await updateMyProfile(profileForm);
    userStore.setUserInfo(info as any);
    ElMessage.success("个人信息已更新");
  } finally {
    savingProfile.value = false;
  }
}

async function savePassword() {
  await passwordFormRef.value?.validate();
  savingPassword.value = true;
  try {
    await changeMyPassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    });
    userStore.refreshUserInfo({ must_change_password: false });
    ElMessage.success("密码修改成功，请重新登录");
  } finally {
    savingPassword.value = false;
  }
}

watch(
  () => userStore.userInfo,
  () => syncFromStore(),
  { immediate: true, deep: true },
);

onMounted(async () => {
  await refreshUser();
});
</script>

<style scoped lang="scss">
.page-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

:deep(.search-card .el-card__body) {
  padding-top: 12px;
  padding-bottom: 12px;
}

:deep(.search-card-head) {
  align-items: center;
}

:deep(.search-card-title) {
  font-size: 18px;
}

:deep(.search-card-tip) {
  align-self: center;
}

.profile-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
}

.profile-grid :deep(.el-card__body) {
  padding-top: 12px;
}

.profile-form {
  max-width: 760px;
}

.profile-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

@media (min-width: 1200px) {
  .profile-grid {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    align-items: start;
  }
}
</style>
