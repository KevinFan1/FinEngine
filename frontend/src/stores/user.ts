import { defineStore } from "pinia";
import { ref, computed } from "vue";
import {
    login as loginApi,
    logout as logoutApi,
    getUserInfo as getUserInfoApi,
} from "@/api/auth";
import type { LoginParams } from "@/api/auth";
import { ElMessage } from "element-plus/es/components/message/index.mjs";
import router from "@/router";

export interface UserInfo {
    id: number;
    username: string;
    display_name: string;
    role: string;
    org_id: number | null;
    org_name?: string;
}

function safeGetToken(): string | null {
    const raw = localStorage.getItem("token");
    return raw && raw !== "undefined" ? raw : null;
}

function safeGetUserInfo(): UserInfo | null {
    try {
        const raw = localStorage.getItem("userInfo");
        if (!raw || raw === "undefined") return null;
        return JSON.parse(raw) as UserInfo;
    } catch {
        return null;
    }
}

export const useUserStore = defineStore("user", () => {
    // State
    const token = ref<string | null>(safeGetToken());
    const userInfo = ref<UserInfo | null>(safeGetUserInfo());

    // Getters
    const isLoggedIn = computed(() => !!token.value);
    const userRole = computed(() => userInfo.value?.role || "");
    const displayName = computed(
        () => userInfo.value?.display_name || userInfo.value?.username || "",
    );
    const isSuperAdmin = computed(() => userInfo.value?.role === "superadmin");
    const isOrgAdmin = computed(() => userInfo.value?.role === "org_admin");

    // Actions
    async function login(params: LoginParams) {
        try {
            const res = await loginApi(params);
            token.value = res.access_token;
            localStorage.setItem("token", res.access_token);

            // Fetch user info after obtaining token
            const info = await getUserInfoApi();
            const user: UserInfo = {
                id: info.id,
                username: info.username,
                display_name: info.display_name,
                role: info.role,
                org_id: info.org_id,
                org_name: info.org_name,
            };
            userInfo.value = user;
            localStorage.setItem("userInfo", JSON.stringify(user));

            ElMessage.success("登录成功");
            await router.push("/dashboard");
        } catch (error) {
            // Clean up on failure
            token.value = null;
            userInfo.value = null;
            localStorage.removeItem("token");
            localStorage.removeItem("userInfo");
            throw error;
        }
    }

    async function logout() {
        try {
            await logoutApi();
        } catch {
            // Ignore logout API errors
        } finally {
            token.value = null;
            userInfo.value = null;
            localStorage.removeItem("token");
            localStorage.removeItem("userInfo");
            router.push("/login");
        }
    }

    function setUserInfo(info: UserInfo) {
        userInfo.value = info;
        localStorage.setItem("userInfo", JSON.stringify(info));
    }

    function clearAuth() {
        token.value = null;
        userInfo.value = null;
        localStorage.removeItem("token");
        localStorage.removeItem("userInfo");
    }

    return {
        token,
        userInfo,
        isLoggedIn,
        userRole,
        displayName,
        isSuperAdmin,
        isOrgAdmin,
        login,
        logout,
        setUserInfo,
        clearAuth,
    };
});
