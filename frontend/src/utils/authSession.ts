import { ElMessage } from "element-plus/es/components/message/index.mjs";
import router from "@/router";
import { clearAuthStorage } from "@/utils/authToken";

const LOGOUT_EVENT = "finengine:auth-logout";
const LOGOUT_STORAGE_KEY = "finengine:auth-logout-event";
const CHANNEL_NAME = "finengine-auth-session";

type LogoutPayload = {
    message?: string;
    redirect?: boolean;
    notify?: boolean;
    ts: number;
};

type ForceLogoutOptions = {
    message?: string;
    redirect?: boolean;
    notify?: boolean;
    broadcast?: boolean;
};

let initialized = false;
let authChannel: BroadcastChannel | null = null;
let lastNotifyAt = 0;

export function subscribeAuthLogout(handler: (payload: LogoutPayload) => void) {
    const listener = (event: Event) => {
        handler((event as CustomEvent<LogoutPayload>).detail);
    };
    window.addEventListener(LOGOUT_EVENT, listener);
    return () => window.removeEventListener(LOGOUT_EVENT, listener);
}

export function initAuthSessionSync() {
    if (initialized || typeof window === "undefined") return;
    initialized = true;

    if ("BroadcastChannel" in window) {
        authChannel = new BroadcastChannel(CHANNEL_NAME);
        authChannel.onmessage = (event: MessageEvent<{ type?: string; payload?: LogoutPayload }>) => {
            if (event.data?.type === "logout" && event.data.payload) {
                applyLogout(event.data.payload, false);
            }
        };
    }

    window.addEventListener("storage", (event) => {
        if (event.key !== LOGOUT_STORAGE_KEY || !event.newValue) return;
        try {
            applyLogout(JSON.parse(event.newValue) as LogoutPayload, false);
        } catch {
            applyLogout({ ts: Date.now(), redirect: true, notify: false }, false);
        }
    });
}

export function forceLogout(options: ForceLogoutOptions = {}) {
    const payload: LogoutPayload = {
        message: options.message,
        redirect: options.redirect ?? true,
        notify: options.notify ?? Boolean(options.message),
        ts: Date.now(),
    };
    applyLogout(payload, options.broadcast ?? true);
}

function applyLogout(payload: LogoutPayload, broadcast: boolean) {
    clearAuthStorage();
    window.dispatchEvent(new CustomEvent<LogoutPayload>(LOGOUT_EVENT, { detail: payload }));

    if (payload.notify && payload.message) {
        notifyOnce(payload.message);
    }

    if (payload.redirect !== false && router.currentRoute.value.path !== "/login") {
        const current = router.currentRoute.value;
        router.push({
            path: "/login",
            query:
                current.fullPath && current.fullPath !== "/"
                    ? { redirect: current.fullPath }
                    : undefined,
        });
    }

    if (broadcast) {
        authChannel?.postMessage({ type: "logout", payload });
        localStorage.setItem(LOGOUT_STORAGE_KEY, JSON.stringify(payload));
    }
}

function notifyOnce(message: string) {
    const now = Date.now();
    if (now - lastNotifyAt < 1500) return;
    lastNotifyAt = now;
    ElMessage.error(message);
}
