<template>
    <div class="login-container">
        <button
            class="theme-switch"
            type="button"
            @click="themeStore.toggleTheme()"
        >
            <el-icon
                ><Moon v-if="themeStore.mode === 'light'" /><Sunny v-else
            /></el-icon>
            <span>{{ themeStore.mode === "light" ? "暗黑" : "明亮" }}</span>
        </button>
        <div class="login-card">
            <div class="login-left">
                <div class="login-left-content">
                    <div class="login-brand-row">
                        <div class="login-logo">
                            <BrandLogo :size="40" />
                        </div>
                        <div>
                            <h1 class="login-brand">FinEngine</h1>
                            <p class="login-brand-desc">财务核算平台</p>
                        </div>
                    </div>

                    <div class="login-summary">
                        <h2>让财务数据整理更简单、更清晰</h2>
                        <p>
                            集中管理平台账单、店铺数据和汇总报表，减少手工整理，让每一次上传和导出都有迹可循。
                        </p>
                    </div>

                    <div class="login-brand-features">
                        <div
                            v-for="feature in featureItems"
                            :key="feature.title"
                            class="feature-item"
                        >
                            <el-icon><Check /></el-icon>
                            <div>
                                <span class="feature-title">{{
                                    feature.title
                                }}</span>
                                <span class="feature-desc">{{
                                    feature.desc
                                }}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="login-right">
                <div class="login-form-wrapper">
                    <div class="login-form-meta">企业工作台</div>
                    <h2 class="login-title">欢迎回来</h2>
                    <p class="login-subtitle">
                        登录后继续处理上传任务、店铺汇总和报表导出。
                    </p>

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

                        <el-form-item prop="captcha_code">
                            <div class="captcha-row">
                                <el-input
                                    v-model="loginForm.captcha_code"
                                    placeholder="请输入验证码"
                                    clearable
                                    maxlength="8"
                                >
                                    <template #prefix>
                                        <el-icon><Key /></el-icon>
                                    </template>
                                </el-input>
                                <button
                                    class="captcha-image"
                                    type="button"
                                    @click="loadCaptcha"
                                >
                                    <img
                                        v-if="captchaImage"
                                        :src="captchaImage"
                                        alt="验证码"
                                    />
                                    <el-icon v-else><RefreshRight /></el-icon>
                                </button>
                            </div>
                        </el-form-item>

                        <el-alert
                            v-if="loginError"
                            class="login-error"
                            :title="loginError"
                            type="error"
                            show-icon
                            :closable="false"
                        />

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
                    <span>&copy; 2025 FinEngine. 财务核算平台</span>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { onMounted, ref, reactive } from "vue";
import type {
    FormInstance,
    FormRules,
} from "element-plus/es/components/form/index.mjs";
import { ElMessage } from "element-plus/es/components/message/index.mjs";
import { useUserStore } from "@/stores/user";
import { useThemeStore } from "@/stores/theme";
import BrandLogo from "@/components/BrandLogo.vue";
import { getCaptcha } from "@/api/auth";

const userStore = useUserStore();
const themeStore = useThemeStore();
const formRef = ref<FormInstance>();
const loading = ref(false);
const captchaImage = ref("");
const loginError = ref("");

const loginForm = reactive({
    username: "",
    password: "",
    captcha_id: "",
    captcha_code: "",
});

const featureItems = [
    { title: "上传即检查", desc: "自动校验账单格式，减少来回核对。" },
    { title: "按店铺汇总", desc: "统一平台、年月和店铺口径。" },
    { title: "导出更省事", desc: "按当前页、选中或全部数据导出。" },
];

const loginRules: FormRules = {
    username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
    password: [{ required: true, message: "请输入密码", trigger: "blur" }],
    captcha_code: [
        { required: true, message: "请输入验证码", trigger: "blur" },
        { min: 4, message: "验证码至少 4 位", trigger: "blur" },
    ],
};

async function loadCaptcha() {
    try {
        const captcha = await getCaptcha();
        loginForm.captcha_id = captcha.captcha_id;
        loginForm.captcha_code = "";
        captchaImage.value = captcha.image;
    } catch (error) {
        loginForm.captcha_id = "";
        captchaImage.value = "";
        const message = getLoginErrorMessage(
            error,
            "验证码加载失败，请刷新页面重试",
        );
        loginError.value = message;
        if (!isApiMessageShown(error)) {
            ElMessage.error(message);
        }
    }
}

async function handleLogin() {
    loginError.value = "";
    const valid = await formRef.value?.validate().catch(() => false);
    if (!valid) return;

    loading.value = true;
    try {
        await userStore.login({
            username: loginForm.username,
            password: loginForm.password,
            captcha_id: loginForm.captcha_id,
            captcha_code: loginForm.captcha_code,
        });
    } catch (error) {
        const message = getLoginErrorMessage(error, "登录失败，请稍后重试");
        loginError.value = message;
        if (!isApiMessageShown(error)) {
            ElMessage.error(message);
        }
        await loadCaptcha().catch(() => undefined);
    } finally {
        loading.value = false;
    }
}

onMounted(() => {
    loadCaptcha().catch(() => undefined);
});

function isApiMessageShown(error: unknown): boolean {
    return Boolean(
        error &&
        typeof error === "object" &&
        (error as { __apiMessageShown?: boolean }).__apiMessageShown,
    );
}

function getLoginErrorMessage(error: unknown, fallback: string): string {
    if (error && typeof error === "object") {
        const shownMessage = (error as { __apiMessageText?: unknown })
            .__apiMessageText;
        if (typeof shownMessage === "string" && shownMessage.trim()) {
            return shownMessage;
        }

        const responseMessage = (
            error as { response?: { data?: { message?: unknown } } }
        ).response?.data?.message;
        if (typeof responseMessage === "string" && responseMessage.trim()) {
            return responseMessage;
        }

        const errorMessage = (error as { message?: unknown }).message;
        if (typeof errorMessage === "string" && errorMessage.trim()) {
            return errorMessage;
        }
    }

    return fallback;
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
    transition:
        background-color 0.12s,
        border-color 0.12s;

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
    background: var(--bg-card);
    border-color: var(--border-color);
    color: var(--text-primary);

    &:hover {
        background: var(--primary-light);
        border-color: var(--primary);
        color: var(--primary);
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
            width: 56px;
            height: 56px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(
                180deg,
                rgba(255, 255, 255, 0.18),
                rgba(255, 255, 255, 0.08)
            );
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 18px;
            box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.06);
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
                    color: #e6f4ff;
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

.captcha-row {
    width: 100%;
    display: grid;
    grid-template-columns: minmax(0, 1fr) 130px;
    gap: 10px;
    align-items: center;
}

.captcha-image {
    width: 130px;
    height: 44px;
    padding: 0;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-btn);
    background: var(--bg-page);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    overflow: hidden;

    img {
        width: 130px;
        height: 44px;
        display: block;
    }

    .el-icon {
        font-size: 18px;
        color: var(--text-secondary);
    }

    &:hover {
        border-color: var(--primary);
    }
}

.login-error {
    margin-bottom: 18px;
    border-radius: var(--radius);
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

    .captcha-row {
        grid-template-columns: 1fr;
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
