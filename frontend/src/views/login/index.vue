<template>
  <div class="login-container">
    <button class="theme-switch" type="button" @click="themeStore.toggleTheme()">
      <el-icon><Moon v-if="themeStore.mode === 'light'" /><Sunny v-else /></el-icon>
      <span>{{ themeStore.mode === 'light' ? '暗黑' : '明亮' }}</span>
    </button>
    <div class="login-card">
      <div class="login-left">
        <div class="login-left-content">
          <div class="login-brand-row">
            <div class="login-logo">
              <svg viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg" width="34" height="34">
                <rect width="28" height="28" rx="6" fill="url(#lg)" />
                <path d="M8 10h12M8 14h8M8 18h10" stroke="#fff" stroke-width="2" stroke-linecap="round" />
                <defs>
                  <linearGradient id="lg" x1="0" y1="0" x2="28" y2="28">
                    <stop stop-color="#93c5fd" />
                    <stop offset="1" stop-color="#2563eb" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <div>
              <h1 class="login-brand">FinEngine</h1>
              <p class="login-brand-desc">财务数据处理系统</p>
            </div>
          </div>

          <div class="login-summary">
            <h2>让财务数据整理更简单、更清晰</h2>
            <p>集中管理平台账单、店铺数据和汇总报表，减少手工整理，让每一次上传和导出都有迹可循。</p>
          </div>

          <div class="login-brand-features">
            <div v-for="feature in featureItems" :key="feature.title" class="feature-item">
              <el-icon><Check /></el-icon>
              <div>
                <span class="feature-title">{{ feature.title }}</span>
                <span class="feature-desc">{{ feature.desc }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="login-right">
        <div class="login-form-wrapper">
          <div class="login-form-meta">企业工作台</div>
          <h2 class="login-title">欢迎回来</h2>
          <p class="login-subtitle">登录后继续处理上传任务、店铺汇总和报表导出。</p>

          <el-form
            ref="formRef"
            :model="loginForm"
            :rules="loginRules"
            label-width="0"
            size="large"
            @keyup.enter="handleLogin"
          >
            <el-form-item prop="username">
              <el-input
                v-model="loginForm.username"
                placeholder="请输入用户名"
                clearable
              >
                <template #prefix>
                  <el-icon><User /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item prop="password">
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="请输入密码"
                show-password
                clearable
              >
                <template #prefix>
                  <el-icon><Lock /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :loading="loading"
                class="login-btn"
                @click="handleLogin"
              >
                登 录
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <div class="login-footer">
          <span>&copy; 2025 FinEngine. All rights reserved.</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import type { FormInstance, FormRules } from 'element-plus/es/components/form/index.mjs'
import { useUserStore } from '@/stores/user'
import { useThemeStore } from '@/stores/theme'

const userStore = useUserStore()
const themeStore = useThemeStore()
const formRef = ref<FormInstance>()
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: '',
})

const featureItems = [
  { title: '上传即检查', desc: '自动校验账单格式，减少来回核对。' },
  { title: '按店铺汇总', desc: '统一平台、年月和店铺口径。' },
  { title: '导出更省事', desc: '按当前页、选中或全部数据导出。' },
]

const loginRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
  ],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await userStore.login({
      username: loginForm.username,
      password: loginForm.password,
    })
  } catch {
    // Error handled in store
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.login-container {
  width: 100%;
  height: 100vh;
  background: var(--login-page-bg);
  display: block;
  overflow: hidden;
}

.theme-switch {
  position: fixed;
  right: 24px;
  top: 24px;
  z-index: 20;
  height: 36px;
  padding: 0 14px;
  border: 1px solid var(--primary);
  border-radius: var(--radius-btn);
  background: var(--primary);
  color: var(--primary-contrast);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  box-shadow: var(--shadow-sm);
  transition: background-color 0.12s, border-color 0.12s;

  .el-icon {
    font-size: 15px;
    color: currentColor;
  }

  span {
    color: currentColor;
  }

  &:hover {
    color: var(--primary-contrast);
    border-color: var(--primary-hover);
    background: var(--primary-hover);
  }
}

:global(html.dark) .theme-switch {
  background: #f8fbff;
  border-color: #f8fbff;
  color: #0f172a;

  &:hover {
    background: #dcecff;
    border-color: #dcecff;
    color: #0f172a;
  }
}

.login-card {
  width: 100%;
  height: 100%;
  background: var(--bg-card);
  display: grid;
  grid-template-columns: minmax(420px, 42%) minmax(480px, 58%);
  overflow: hidden;
}

.login-left {
  background: var(--brand-panel-bg);
  border-right: 1px solid var(--border-light);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(48px, 6vw, 96px);

  .login-left-content {
    color: var(--brand-panel-text);
    width: min(500px, 100%);
    text-align: left;

    .login-brand-row {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 60px;
    }

    .login-logo {
      width: 48px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(255, 255, 255, 0.12);
      border: 1px solid rgba(255, 255, 255, 0.18);
      border-radius: 10px;
    }

    .login-brand {
      font-size: 26px;
      font-weight: 700;
      line-height: 1.1;
      margin-bottom: 4px;
      letter-spacing: 0;
    }

    .login-brand-desc {
      font-size: 13px;
      opacity: 0.9;
    }

    .login-summary {
      margin-bottom: 42px;

      h2 {
        max-width: 480px;
        font-size: clamp(30px, 3.2vw, 44px);
        font-weight: 700;
        line-height: 1.22;
        margin-bottom: 18px;
        letter-spacing: 0;
      }

      p {
        max-width: 460px;
        font-size: 15px;
        line-height: 1.8;
        color: rgba(255, 255, 255, 0.78);
      }
    }

    .login-brand-features {
      text-align: left;
      display: grid;
      gap: 18px;

      .feature-item {
        display: flex;
        align-items: flex-start;
        gap: 12px;

        .el-icon {
          color: #bfdbfe;
          margin-top: 3px;
          flex-shrink: 0;
        }

        .feature-title,
        .feature-desc {
          display: block;
        }

        .feature-title {
          font-size: 15px;
          font-weight: 600;
          line-height: 1.35;
        }

        .feature-desc {
          margin-top: 3px;
          color: rgba(255, 255, 255, 0.72);
          font-size: 13px;
          line-height: 1.5;
        }
      }
    }
  }
}

.login-right {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: clamp(40px, 6vw, 96px);
  position: relative;
  background: var(--bg-card);

  .login-form-wrapper {
    width: 100%;
    max-width: 408px;

    .login-title {
      font-size: 28px;
      font-weight: 700;
      color: var(--text-primary);
      margin-bottom: 8px;
    }

    .login-subtitle {
      font-size: 14px;
      color: var(--text-secondary);
      margin-bottom: 32px;
    }
  }

  .login-footer {
    position: absolute;
    bottom: 32px;
    left: 0;
    right: 0;
    text-align: center;

    span {
      font-size: 12px;
      color: var(--text-tertiary);
    }
  }
}

.login-btn {
  width: 100%;
  height: 46px;
  font-size: 15px;
  font-weight: 500;
  border-radius: var(--radius-btn);
}

@media (max-width: 1024px) {
  .login-card {
    grid-template-columns: 1fr;
    overflow: auto;
  }

  .login-left {
    min-height: auto;
    align-items: flex-start;

    .login-brand-features {
      display: none;
    }
  }

  .login-right {
    min-height: 460px;
  }
}

@media (max-width: 640px) {
  .theme-switch {
    right: 16px;
    top: 16px;
  }

  .login-left,
  .login-right {
    padding: 32px 22px;
  }

  .login-left {
    .login-left-content {
      .login-brand-row,
      .login-summary {
        margin-bottom: 24px;
      }
    }
  }
}
</style>
