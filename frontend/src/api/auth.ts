import { get, post } from "./index";

export interface LoginParams {
    username: string;
    password: string;
    captcha_id: string;
    captcha_code: string;
}

export interface LoginResult {
    access_token: string;
    token_type: string;
}

export interface CaptchaResult {
    captcha_id: string;
    image: string;
    expires_in: number;
}

export interface UserInfo {
    id: number;
    username: string;
    display_name: string;
    phone: string;
    email: string;
    role: string;
    org_id: number | null;
    org_name?: string;
    status: string;
    last_login_at: string | null;
    created_at: string;
}

/**
 * User login
 */
export function login(data: LoginParams) {
    return post<LoginResult>("/auth/login", data);
}

/**
 * Get login captcha
 */
export function getCaptcha() {
    return get<CaptchaResult>("/auth/captcha");
}

/**
 * User logout
 */
export function logout() {
    return post<null>("/auth/logout");
}

/**
 * Get current user info
 */
export function getUserInfo() {
    return get<UserInfo>("/auth/me");
}
