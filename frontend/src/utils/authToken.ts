export function normalizeAuthToken(raw: string | null | undefined): string | null {
    if (!raw || raw === "undefined" || raw === "null") return null;
    return raw;
}

export function getStoredAuthToken(): string | null {
    if (typeof window === "undefined") return null;
    return normalizeAuthToken(localStorage.getItem("token"));
}

export function clearAuthStorage() {
    localStorage.removeItem("token");
    localStorage.removeItem("userInfo");
}

export function authTokenExpiresAtMs(token: string | null | undefined): number | null {
    const payload = decodeJwtPayload(token);
    if (!payload || typeof payload.exp !== "number") return null;
    return payload.exp * 1000;
}

export function isAuthTokenExpired(
    token: string | null | undefined,
    skewMs = 0,
): boolean {
    const expiresAt = authTokenExpiresAtMs(token);
    if (!expiresAt) return true;
    return expiresAt <= Date.now() + skewMs;
}

function decodeJwtPayload(token: string | null | undefined): { exp?: number } | null {
    const normalized = normalizeAuthToken(token);
    if (!normalized) return null;
    const parts = normalized.split(".");
    if (parts.length < 2) return null;

    try {
        const payloadText = atob(toPaddedBase64(parts[1]));
        return JSON.parse(payloadText) as { exp?: number };
    } catch {
        return null;
    }
}

function toPaddedBase64(base64Url: string): string {
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    return base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
}
