<template>
  <el-dialog
    v-model="visible"
    title="首次登录需要修改密码"
    width="520px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    destroy-on-close
  >
    <el-alert
      type="warning"
      :closable="false"
      title="当前账号使用初始密码，请先修改后继续使用。"
      style="margin-bottom: 16px"
    />

    <p style="line-height: 1.8; margin: 0">
      你的账号当前使用初始密码。请先进入个人中心修改密码后再继续使用系统。
    </p>

    <template #footer>
      <el-button type="primary" @click="handleGoProfile">去个人中心</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
defineOptions({ name: "ForcePasswordChangeDialog" });

import { useRouter } from "vue-router";

const visible = defineModel<boolean>({ default: false });
const router = useRouter();

function handleGoProfile() {
  visible.value = false;
  router.push("/profile");
}
</script>
