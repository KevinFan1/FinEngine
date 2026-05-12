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

export class ApiBusinessError extends Error {
    code: number;
    data?: unknown;

    constructor(message: string, code: number, data?: unknown) {
        super(message);
        this.name = "ApiBusinessError";
        this.code = code;
        this.data = data;
    }
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

        // Backend returns HTTP 200 for business errors and exposes the real state in code/message.
        if (res.code !== undefined && res.code !== 200) {
            const message = res.message || "请求失败";
            ElMessage.error(message);

            if (res.code === 401) {
                localStorage.removeItem("token");
                localStorage.removeItem("userInfo");
                router.push("/login");
            }

            return Promise.reject(new ApiBusinessError(message, res.code, res.data));
        }

        return response;
    },
    (error) => {
        if (error.response) {
            const status = error.response.status;
            const data = error.response.data;

            const message = data?.message || `请求失败 (${status})`;
            ElMessage.error(message);

            if (status === 401 || data?.code === 401) {
                localStorage.removeItem("token");
                localStorage.removeItem("userInfo");
                router.push("/login");
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
    const blob = response.data as Blob;
    const contentType = response.headers["content-type"] || blob.type;
    if (contentType?.includes("application/json")) {
        const text = await blob.text();
        const parsed = JSON.parse(text) as ApiResponse;
        if (parsed.code !== 200) {
            const message = parsed.message || "导出失败";
            ElMessage.error(message);
            throw new ApiBusinessError(message, parsed.code, parsed.data);
        }
    }
    return blob;
}

export default service;
