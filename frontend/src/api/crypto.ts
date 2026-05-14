import type {
    AxiosResponse,
    InternalAxiosRequestConfig,
} from "axios";

interface CryptoPublicKey {
    enabled: boolean;
    key_id: string;
    public_key: string;
}

interface EncryptedEnvelope {
    encrypted: true;
    iv: string;
    data: string;
}

let cryptoKeyCache: CryptoKey | null = null;
let cryptoKeyId = "";
const sessionKeys = new WeakMap<InternalAxiosRequestConfig, CryptoKey>();

export async function encryptRequest(config: InternalAxiosRequestConfig) {
    if (!shouldEncrypt(config)) return config;

    const publicKey = getPublicKey();
    if (!publicKey?.enabled) return config;

    const timestamp = String(Date.now());
    const nonce = createNonce();
    const aad = new TextEncoder().encode(`${timestamp}:${nonce}`);
    const aesKey = await crypto.subtle.generateKey(
        { name: "AES-GCM", length: 256 },
        true,
        ["encrypt", "decrypt"],
    );
    const rawAesKey = await crypto.subtle.exportKey("raw", aesKey);
    const rsaKey = await importRsaPublicKey(publicKey);
    const encryptedKeyPayload = new TextEncoder().encode(JSON.stringify({
        key: arrayBufferToBase64(rawAesKey),
        timestamp,
        nonce,
    }));
    const encryptedKey = await crypto.subtle.encrypt(
        { name: "RSA-OAEP" },
        rsaKey,
        encryptedKeyPayload,
    );
    if (hasRequestBody(config)) {
        const plaintext = new TextEncoder().encode(JSON.stringify(config.data ?? {}));
        const iv = crypto.getRandomValues(new Uint8Array(12));
        const ciphertext = await crypto.subtle.encrypt(
            { name: "AES-GCM", iv, additionalData: aad },
            aesKey,
            plaintext,
        );

        config.data = {
            encrypted: true,
            iv: arrayBufferToBase64(iv),
            data: arrayBufferToBase64(ciphertext),
        } satisfies EncryptedEnvelope;
    }
    config.headers.set("X-API-Encrypted", "1");
    config.headers.set("X-API-Crypto-Key", arrayBufferToBase64(encryptedKey));
    config.headers.set("X-API-Crypto-Key-Id", publicKey.key_id);
    config.headers.set("X-API-Timestamp", timestamp);
    config.headers.set("X-API-Nonce", nonce);
    sessionKeys.set(config, aesKey);
    return config;
}

export async function decryptResponse(response: AxiosResponse) {
    if (response.headers["x-api-encrypted-response"] !== "1") return response;
    const envelope = response.data as EncryptedEnvelope;
    if (!envelope?.encrypted) return response;

    const aesKey = sessionKeys.get(response.config);
    if (!aesKey) {
        throw new Error("响应解密失败：缺少会话密钥");
    }

    const plaintext = await crypto.subtle.decrypt(
        { name: "AES-GCM", iv: base64ToUint8Array(envelope.iv) },
        aesKey,
        base64ToUint8Array(envelope.data),
    );
    response.data = JSON.parse(new TextDecoder().decode(plaintext));
    return response;
}

function shouldEncrypt(config: InternalAxiosRequestConfig): boolean {
    if (!window.crypto?.subtle) return false;
    const method = (config.method || "GET").toUpperCase();
    if (!["GET", "POST", "PUT", "PATCH", "DELETE"].includes(method)) return false;
    if (config.responseType === "blob") return false;
    if (isFormData(config.data)) return false;
    return Boolean(import.meta.env.VITE_API_CRYPTO_PUBLIC_KEY);
}

function hasRequestBody(config: InternalAxiosRequestConfig): boolean {
    const method = (config.method || "GET").toUpperCase();
    return !["GET", "HEAD"].includes(method);
}

function isFormData(data: unknown): boolean {
    return typeof FormData !== "undefined" && data instanceof FormData;
}

function getPublicKey(): CryptoPublicKey | null {
    const publicKey = import.meta.env.VITE_API_CRYPTO_PUBLIC_KEY?.trim();
    if (!publicKey) return null;
    const normalized = publicKey.includes("BEGIN PUBLIC KEY")
        ? publicKey.replace(/\\n/g, "\n")
        : publicKey.replace(/\s/g, "");
    return {
        enabled: true,
        key_id: import.meta.env.VITE_API_CRYPTO_KEY_ID || "static",
        public_key: normalized,
    };
}

async function importRsaPublicKey(publicKey: CryptoPublicKey): Promise<CryptoKey> {
    if (cryptoKeyCache && cryptoKeyId === publicKey.key_id) return cryptoKeyCache;
    const der = publicKey.public_key.includes("BEGIN PUBLIC KEY")
        ? pemToArrayBuffer(publicKey.public_key)
        : base64ToUint8Array(publicKey.public_key).buffer;
    cryptoKeyCache = await crypto.subtle.importKey(
        "spki",
        der,
        { name: "RSA-OAEP", hash: "SHA-256" },
        false,
        ["encrypt"],
    );
    cryptoKeyId = publicKey.key_id;
    return cryptoKeyCache;
}

function pemToArrayBuffer(pem: string): ArrayBuffer {
    const base64 = pem
        .replace(/-----BEGIN PUBLIC KEY-----/g, "")
        .replace(/-----END PUBLIC KEY-----/g, "")
        .replace(/\s/g, "");
    return base64ToUint8Array(base64).buffer;
}

function arrayBufferToBase64(buffer: ArrayBuffer | Uint8Array): string {
    const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
    let binary = "";
    bytes.forEach((byte) => {
        binary += String.fromCharCode(byte);
    });
    return btoa(binary);
}

function createNonce(): string {
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    return arrayBufferToBase64(bytes);
}

function base64ToUint8Array(base64: string): Uint8Array {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
        bytes[index] = binary.charCodeAt(index);
    }
    return bytes;
}
