import axios, {
    type AxiosInstance,
    type AxiosResponse,
    type InternalAxiosRequestConfig,
} from "axios";
import { ElMessage } from "element-plus/es/components/message/index.mjs";
import router from "@/router";

// API response wrapper type
export interface ApiResponse<T = any> {
    code: number;
    message: string;
    data: T;
}

// Paginated response type
export interface PaginatedData<T = any> {
    items: T[];
    total: number;
    page: number;
    page_size: number;
}

// Create Axios instance
const service: AxiosInstance = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL,
    timeout: 30000,
    headers: {
        "Content-Type": "application/json",
    },
});

// Request interceptor - inject JWT token
service.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem("token");
        if (token && config.headers) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    },
);

// Response interceptor - handle errors
service.interceptors.response.use(
    (response: AxiosResponse<ApiResponse>) => {
        const res = response.data;

        // If the API wraps responses in { code, message, data }
        if (res.code !== undefined && res.code !== 200) {
            ElMessage.error(res.message || "请求失败");

            // 401 Unauthorized - clear token and redirect to login
            if (res.code === 401) {
                localStorage.removeItem("token");
                localStorage.removeItem("userInfo");
                router.push("/login");
            }

            return Promise.reject(new Error(res.message || "请求失败"));
        }

        return response;
    },
    (error) => {
        if (error.response) {
            const status = error.response.status;
            const data = error.response.data;

            switch (status) {
                case 401:
                    ElMessage.error("登录已过期，请重新登录");
                    localStorage.removeItem("token");
                    localStorage.removeItem("userInfo");
                    router.push("/login");
                    break;
                case 403:
                    ElMessage.error("没有权限执行此操作");
                    break;
                case 404:
                    ElMessage.error("请求的资源不存在");
                    break;
                case 500:
                    ElMessage.error(data?.message || "服务器内部错误");
                    break;
                default:
                    ElMessage.error(data?.message || `请求失败 (${status})`);
            }
        } else if (error.message?.includes("timeout")) {
            ElMessage.error("请求超时，请稍后重试");
        } else {
            ElMessage.error("网络异常，请检查网络连接");
        }

        return Promise.reject(error);
    },
);

/**
 * Generic request method
 */
export async function request<T>(
    config: InternalAxiosRequestConfig,
): Promise<T> {
    const response = await service.request<ApiResponse<T>>(config);
    return response.data.data;
}

/**
 * GET request
 */
export async function get<T>(
    url: string,
    params?: Record<string, any>,
): Promise<T> {
    return request<T>({
        url,
        method: "GET",
        params,
    } as InternalAxiosRequestConfig);
}

/**
 * POST request
 */
export async function post<T>(url: string, data?: any): Promise<T> {
    return request<T>({
        url,
        method: "POST",
        data,
    } as InternalAxiosRequestConfig);
}

/**
 * PUT request
 */
export async function put<T>(url: string, data?: any): Promise<T> {
    return request<T>({
        url,
        method: "PUT",
        data,
    } as InternalAxiosRequestConfig);
}

/**
 * DELETE request
 */
export async function del<T>(
    url: string,
    params?: Record<string, any>,
): Promise<T> {
    return request<T>({
        url,
        method: "DELETE",
        params,
    } as InternalAxiosRequestConfig);
}

/**
 * Download blob (for file exports)
 */
export async function downloadBlob(
    url: string,
    params?: Record<string, any>,
): Promise<Blob> {
    const response = await service.get(url, { params, responseType: "blob" });
    return response.data;
}

export default service;
