import axios, {
    type AxiosInstance,
    type AxiosResponse,
    type InternalAxiosRequestConfig,
} from "axios";
import { ElMessage } from "element-plus/es/components/message/index.mjs";
import { decryptResponse, encryptRequest } from "@/api/crypto";
import { forceLogout } from "@/utils/authSession";

// API response wrapper type
export interface ApiResponse<T = any> {
    code: number;
    message: string;
    data: T;
}

export class ApiBusinessError extends Error {
    code: number;
    data?: unknown;
    __apiMessageShown?: boolean;
    __apiMessageText?: string;

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
    async (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem("token");
        if (token && config.headers) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        try {
            return await encryptRequest(config);
        } catch (error) {
            showRequestError("请求加密失败，请刷新页面后重试", error);
            return Promise.reject(error);
        }
    },
    (error) => {
        return Promise.reject(error);
    },
);

// Response interceptor - handle errors
service.interceptors.response.use(
    async (rawResponse: AxiosResponse<ApiResponse>) => {
        let response: AxiosResponse<ApiResponse>;
        try {
            response = await decryptResponse(rawResponse);
        } catch (error) {
            showRequestError("响应解密失败，请刷新页面后重试", error);
            return Promise.reject(error);
        }
        const res = response.data;

        // Backend returns HTTP 200 for business errors and exposes the real state in code/message.
        if (res.code !== undefined && res.code !== 200) {
            const message = authExpiredMessage(res.code, res.message || "请求失败");

            if (res.code === 401) {
                forceLogout({ message });
            } else {
                ElMessage.error(message);
            }

            const error = new ApiBusinessError(message, res.code, res.data);
            markRequestErrorShown(error, message);
            return Promise.reject(error);
        }

        return response;
    },
    (error) => {
        if (isRequestErrorShown(error)) {
            return Promise.reject(error);
        }

        if (error.response) {
            const status = error.response.status;
            const data = error.response.data;

            const message = authExpiredMessage(status, data?.message || `请求失败 (${status})`);
            markRequestErrorShown(error, message);

            if (status === 401 || data?.code === 401) {
                forceLogout({ message });
            } else {
                ElMessage.error(message);
            }
        } else if (error.message?.includes("timeout")) {
            const message = "请求超时，请稍后重试";
            ElMessage.error(message);
            markRequestErrorShown(error, message);
        } else {
            const message = "网络异常，请检查网络连接";
            ElMessage.error(message);
            markRequestErrorShown(error, message);
        }

        return Promise.reject(error);
    },
);

function showRequestError(message: string, error: unknown) {
    ElMessage.error(message);
    markRequestErrorShown(error, message);
}

function authExpiredMessage(code: number, message: string) {
    if (code === 401 && message.includes("其他端登录")) {
        return "账号已在其他端登录，请重新登录";
    }
    return message;
}

function markRequestErrorShown(error: unknown, message: string) {
    if (error && typeof error === "object") {
        const requestError = error as {
            __apiMessageShown?: boolean;
            __apiMessageText?: string;
        };
        requestError.__apiMessageShown = true;
        requestError.__apiMessageText = message;
    }
}

function isRequestErrorShown(error: unknown): boolean {
    return Boolean(
        error &&
        typeof error === "object" &&
        (error as { __apiMessageShown?: boolean }).__apiMessageShown,
    );
}

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
 * Multipart form upload
 */
export async function uploadForm<T>(url: string, data: FormData): Promise<T> {
    const response = await service.post<ApiResponse<T>>(url, data, {
        headers: {
            "Content-Type": "multipart/form-data",
        },
    });
    return response.data.data;
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
