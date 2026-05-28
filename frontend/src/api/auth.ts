import { get, post, put } from "./index";

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
    must_change_password: boolean;
    role: string;
    org_id: number | null;
    org_name?: string;
    status: string;
    last_login_at: string | null;
    created_at: string;
}

export interface UpdateMePayload {
    display_name: string;
    phone: string;
}

export interface ChangeMyPasswordPayload {
    old_password: string;
    new_password: string;
}

export interface UserPreferenceResult<T = unknown> {
    preference_key: string;
    preference_value: T;
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

export function updateMyProfile(data: UpdateMePayload) {
    return put<UserInfo>("/auth/me", data);
}

export function changeMyPassword(data: ChangeMyPasswordPayload) {
    return put<void>("/auth/me/password", data);
}

export function getMyPreference<T = unknown>(preferenceKey: string) {
    return get<UserPreferenceResult<T> | null>(`/auth/me/preferences/${preferenceKey}`);
}

export function updateMyPreference<T = unknown>(preferenceKey: string, preferenceValue: T) {
    return put<UserPreferenceResult<T>>(`/auth/me/preferences/${preferenceKey}`, {
        preference_value: preferenceValue,
    });
}
