import forge from "node-forge";
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

interface SessionKey {
    raw: Uint8Array;
    subtle?: CryptoKey;
}

let cryptoKeyCache: CryptoKey | null = null;
let cryptoKeyId = "";
const sessionKeys = new WeakMap<InternalAxiosRequestConfig, SessionKey>();

export async function encryptRequest(config: InternalAxiosRequestConfig) {
    if (!shouldEncrypt(config)) return config;

    const publicKey = getPublicKey();
    if (!publicKey?.enabled) {
        throw new Error("请求加密失败：缺少接口加密公钥");
    }

    const timestamp = String(Date.now());
    const nonce = createNonce();
    const aad = new TextEncoder().encode(`${timestamp}:${nonce}`);
    const rawAesKey = randomBytes(32);
    const encryptedKey = await encryptAesKey(publicKey, rawAesKey, timestamp, nonce);
    const sessionKey: SessionKey = { raw: rawAesKey };

    if (hasRequestBody(config) && !isFormData(config.data)) {
        const plaintext = new TextEncoder().encode(JSON.stringify(config.data ?? {}));
        const encryptedBody = await encryptPayload(rawAesKey, plaintext, aad);
        config.data = encryptedBody;
    }

    config.headers.set("X-API-Encrypted", "1");
    config.headers.set("X-API-Crypto-Key", arrayBufferToBase64(encryptedKey));
    config.headers.set("X-API-Crypto-Key-Id", publicKey.key_id);
    config.headers.set("X-API-Timestamp", timestamp);
    config.headers.set("X-API-Nonce", nonce);
    sessionKeys.set(config, sessionKey);
    return config;
}

export async function decryptResponse(response: AxiosResponse) {
    if (response.headers["x-api-encrypted-response"] !== "1") return response;
    const envelope = await responseEnvelope(response.data);
    if (!envelope?.encrypted) return response;

    const sessionKey = sessionKeys.get(response.config);
    if (!sessionKey) {
        throw new Error("响应解密失败：缺少会话密钥");
    }

    const plaintext = await decryptPayload(sessionKey, envelope);
    response.data = JSON.parse(new TextDecoder().decode(plaintext));
    return response;
}

function shouldEncrypt(config: InternalAxiosRequestConfig): boolean {
    const method = (config.method || "GET").toUpperCase();
    if (!["GET", "POST", "PUT", "PATCH", "DELETE"].includes(method)) return false;
    return true;
}

function hasRequestBody(config: InternalAxiosRequestConfig): boolean {
    const method = (config.method || "GET").toUpperCase();
    return !["GET", "HEAD"].includes(method);
}

function isFormData(data: unknown): boolean {
    return typeof FormData !== "undefined" && data instanceof FormData;
}

async function responseEnvelope(data: unknown): Promise<EncryptedEnvelope | null> {
    if (data instanceof Blob) {
        return JSON.parse(await data.text()) as EncryptedEnvelope;
    }
    return data as EncryptedEnvelope;
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

async function encryptAesKey(
    publicKey: CryptoPublicKey,
    rawAesKey: Uint8Array,
    timestamp: string,
    nonce: string,
): Promise<ArrayBuffer | Uint8Array> {
    const payload = new TextEncoder().encode(JSON.stringify({
        key: arrayBufferToBase64(rawAesKey),
        timestamp,
        nonce,
    }));

    if (hasSubtleCrypto()) {
        const rsaKey = await importRsaPublicKey(publicKey);
        return crypto.subtle.encrypt({ name: "RSA-OAEP" }, rsaKey, payload);
    }

    const rsaKey = forge.pki.publicKeyFromPem(publicKeyToPem(publicKey.public_key));
    const encrypted = rsaKey.encrypt(bytesToForgeBinary(payload), "RSA-OAEP", {
        md: forge.md.sha256.create(),
        mgf1: {
            md: forge.md.sha256.create(),
        },
    });
    return forgeBinaryToBytes(encrypted);
}

async function encryptPayload(
    rawAesKey: Uint8Array,
    plaintext: Uint8Array,
    aad: Uint8Array,
): Promise<EncryptedEnvelope> {
    const iv = randomBytes(12);
    let ciphertext: ArrayBuffer | Uint8Array;

    if (hasSubtleCrypto()) {
        const aesKey = await crypto.subtle.importKey("raw", rawAesKey, "AES-GCM", false, ["encrypt"]);
        ciphertext = await crypto.subtle.encrypt(
            { name: "AES-GCM", iv, additionalData: aad },
            aesKey,
            plaintext,
        );
    } else {
        const cipher = forge.cipher.createCipher("AES-GCM", bytesToForgeBinary(rawAesKey));
        cipher.start({
            iv: bytesToForgeBinary(iv),
            additionalData: bytesToForgeBinary(aad),
            tagLength: 128,
        });
        cipher.update(forge.util.createBuffer(bytesToForgeBinary(plaintext), "raw"));
        cipher.finish();
        ciphertext = forgeBinaryToBytes(cipher.output.getBytes() + cipher.mode.tag.getBytes());
    }

    return {
        encrypted: true,
        iv: arrayBufferToBase64(iv),
        data: arrayBufferToBase64(ciphertext),
    };
}

async function decryptPayload(sessionKey: SessionKey, envelope: EncryptedEnvelope): Promise<ArrayBuffer | Uint8Array> {
    const iv = base64ToUint8Array(envelope.iv);
    const encrypted = base64ToUint8Array(envelope.data);

    if (hasSubtleCrypto()) {
        const subtleKey = sessionKey.subtle || await crypto.subtle.importKey(
            "raw",
            sessionKey.raw,
            "AES-GCM",
            false,
            ["decrypt"],
        );
        sessionKey.subtle = subtleKey;
        return crypto.subtle.decrypt({ name: "AES-GCM", iv }, subtleKey, encrypted);
    }

    const tagLength = 16;
    const ciphertext = encrypted.slice(0, encrypted.length - tagLength);
    const tag = encrypted.slice(encrypted.length - tagLength);
    const decipher = forge.cipher.createDecipher("AES-GCM", bytesToForgeBinary(sessionKey.raw));
    decipher.start({
        iv: bytesToForgeBinary(iv),
        tag: forge.util.createBuffer(bytesToForgeBinary(tag), "raw"),
        tagLength: 128,
    });
    decipher.update(forge.util.createBuffer(bytesToForgeBinary(ciphertext), "raw"));

    if (!decipher.finish()) {
        throw new Error("响应解密失败：密文校验失败");
    }
    return forgeBinaryToBytes(decipher.output.getBytes());
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

function hasSubtleCrypto(): boolean {
    return Boolean(window.crypto?.subtle);
}

function publicKeyToPem(publicKey: string): string {
    if (publicKey.includes("BEGIN PUBLIC KEY")) return publicKey;
    const lines = publicKey.match(/.{1,64}/g)?.join("\n") || publicKey;
    return `-----BEGIN PUBLIC KEY-----\n${lines}\n-----END PUBLIC KEY-----`;
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
    return arrayBufferToBase64(randomBytes(16));
}

function randomBytes(length: number): Uint8Array {
    if (window.crypto?.getRandomValues) {
        return window.crypto.getRandomValues(new Uint8Array(length));
    }
    return forgeBinaryToBytes(forge.random.getBytesSync(length));
}

function base64ToUint8Array(base64: string): Uint8Array {
    const binary = atob(base64);
    return forgeBinaryToBytes(binary);
}

function bytesToForgeBinary(bytes: Uint8Array): string {
    let binary = "";
    bytes.forEach((byte) => {
        binary += String.fromCharCode(byte);
    });
    return binary;
}

function forgeBinaryToBytes(binary: string): Uint8Array {
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
        bytes[index] = binary.charCodeAt(index);
    }
    return bytes;
}
