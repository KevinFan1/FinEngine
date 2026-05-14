"""RSA/AES helpers for transparent API payload encryption."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from dataclasses import dataclass

import redis.asyncio as redis
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


@dataclass(frozen=True)
class EncryptedPayload:
    iv: str
    data: str


@dataclass(frozen=True)
class ReplayCheckResult:
    ok: bool
    message: str = ""


class ApiCryptoService:
    def __init__(self) -> None:
        self._private_key = self._load_private_key()
        public_der = self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.key_id = hashlib.sha256(public_der).hexdigest()[:16]

    @property
    def public_key_pem(self) -> str:
        return self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    def decrypt_aes_key(self, encrypted_key: str, *, timestamp: str, nonce: str) -> bytes:
        encrypted = base64.b64decode(encrypted_key)
        decrypted = self._private_key.decrypt(
            encrypted,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        payload = json.loads(decrypted.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Encrypted key payload is invalid")
        if str(payload.get("timestamp") or "") != timestamp or str(payload.get("nonce") or "") != nonce:
            raise ValueError("Encrypted key replay fields do not match request headers")
        key = base64.b64decode(str(payload.get("key") or ""))
        if len(key) != 32:
            raise ValueError("AES key length is invalid")
        return key

    def decrypt_payload(self, aes_key: bytes, *, iv: str, data: str, aad: bytes | None = None) -> bytes:
        aesgcm = AESGCM(aes_key)
        return aesgcm.decrypt(base64.b64decode(iv), base64.b64decode(data), aad)

    def encrypt_payload(self, aes_key: bytes, plaintext: bytes, *, aad: bytes | None = None) -> EncryptedPayload:
        iv = os.urandom(12)
        ciphertext = AESGCM(aes_key).encrypt(iv, plaintext, aad)
        return EncryptedPayload(
            iv=base64.b64encode(iv).decode("ascii"),
            data=base64.b64encode(ciphertext).decode("ascii"),
        )

    def _load_private_key(self):
        private_key = settings.API_CRYPTO_PRIVATE_KEY.strip()
        if private_key:
            private_key = private_key.replace("\\n", "\n")
            return serialization.load_pem_private_key(private_key.encode("utf-8"), password=None)

        if settings.API_CRYPTO_ENABLED:
            raise ValueError("API_CRYPTO_ENABLED=true 时必须配置 API_CRYPTO_PRIVATE_KEY，并把对应公钥配置到前端 VITE_API_CRYPTO_PUBLIC_KEY")

        return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class ApiReplayGuard:
    def __init__(self) -> None:
        self._redis: redis.Redis | None = None
        self._memory: dict[str, float] = {}

    async def verify(self, timestamp: str, nonce: str) -> ReplayCheckResult:
        timestamp_ms = _parse_timestamp_ms(timestamp)
        if timestamp_ms is None:
            return ReplayCheckResult(ok=False, message="请求时间戳无效")

        window_seconds = settings.API_CRYPTO_REPLAY_WINDOW_SECONDS
        now_ms = int(time.time() * 1000)
        if abs(now_ms - timestamp_ms) > window_seconds * 1000:
            return ReplayCheckResult(ok=False, message="请求已过期，请刷新后重试")

        nonce = nonce.strip()
        if len(nonce) < 16 or len(nonce) > 128:
            return ReplayCheckResult(ok=False, message="请求 nonce 无效")

        stored = await self._mark_nonce(nonce, ttl_seconds=window_seconds)
        if not stored:
            return ReplayCheckResult(ok=False, message="请求已重复提交，请刷新后重试")
        return ReplayCheckResult(ok=True)

    async def _mark_nonce(self, nonce: str, *, ttl_seconds: int) -> bool:
        nonce_hash = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
        redis_result = await self._mark_nonce_redis(nonce_hash, ttl_seconds=ttl_seconds)
        if redis_result is not None:
            return redis_result
        return self._mark_nonce_memory(nonce_hash, ttl_seconds=ttl_seconds)

    async def _mark_nonce_redis(self, nonce_hash: str, *, ttl_seconds: int) -> bool | None:
        try:
            client = self._redis_client()
            return bool(await client.set(f"finengine:api_nonce:{nonce_hash}", "1", ex=ttl_seconds, nx=True))
        except Exception:
            return None

    def _mark_nonce_memory(self, nonce_hash: str, *, ttl_seconds: int) -> bool:
        now = time.time()
        expired = [key for key, expires_at in self._memory.items() if expires_at < now]
        for key in expired:
            self._memory.pop(key, None)

        if nonce_hash in self._memory:
            return False
        self._memory[nonce_hash] = now + ttl_seconds
        return True

    def _redis_client(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis


def replay_aad(timestamp: str, nonce: str) -> bytes:
    return f"{timestamp}:{nonce}".encode("utf-8")


def _parse_timestamp_ms(timestamp: str) -> int | None:
    try:
        value = int(timestamp)
    except (TypeError, ValueError):
        return None
    if value < 10_000_000_000:
        value *= 1000
    return value


api_crypto_service = ApiCryptoService()
api_replay_guard = ApiReplayGuard()
