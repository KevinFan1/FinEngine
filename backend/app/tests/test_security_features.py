import pytest

from app.core.security import create_access_token, decode_access_token
from app.services.captcha_service import CaptchaService
from app.services.crypto_service import ApiReplayGuard, api_crypto_service, replay_aad
from app.services.oss_service import _internal_oss_host


@pytest.mark.asyncio
async def test_captcha_is_one_time_memory_fallback() -> None:
    service = CaptchaService()

    async def save_to_redis(_captcha_id: str, _code: str) -> bool:
        return False

    async def pop_from_redis(_captcha_id: str) -> str | None:
        return None

    service._save_to_redis = save_to_redis  # type: ignore[method-assign]
    service._pop_from_redis = pop_from_redis  # type: ignore[method-assign]

    challenge = await service.generate()
    code = service._store[challenge.captcha_id][0]

    assert await service.verify(challenge.captcha_id, code)
    assert not await service.verify(challenge.captcha_id, code)


def test_crypto_payload_round_trip() -> None:
    key = b"1" * 32
    plaintext = b'{"ok":true}'

    encrypted = api_crypto_service.encrypt_payload(key, plaintext, aad=replay_aad("1710000000000", "nonce-1234567890"))

    assert api_crypto_service.decrypt_payload(
        key,
        iv=encrypted.iv,
        data=encrypted.data,
        aad=replay_aad("1710000000000", "nonce-1234567890"),
    ) == plaintext


@pytest.mark.asyncio
async def test_replay_guard_rejects_duplicate_nonce() -> None:
    guard = ApiReplayGuard()

    async def mark_nonce_redis(_nonce_hash: str, *, ttl_seconds: int) -> bool | None:
        return None

    guard._mark_nonce_redis = mark_nonce_redis  # type: ignore[method-assign]

    import time

    timestamp = str(int(time.time() * 1000))
    nonce = "nonce-1234567890abcdef"
    assert (await guard.verify(timestamp, nonce)).ok
    assert not (await guard.verify(timestamp, nonce)).ok


def test_internal_oss_host_is_derived_from_public_endpoint() -> None:
    assert _internal_oss_host("oss-cn-guangzhou.aliyuncs.com") == "oss-cn-guangzhou-internal.aliyuncs.com"
    assert _internal_oss_host("oss-cn-guangzhou-internal.aliyuncs.com") == "oss-cn-guangzhou-internal.aliyuncs.com"


def test_access_token_carries_session_id() -> None:
    token = create_access_token(subject=123, session_id="session-abc")
    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "123"
    assert payload["sid"] == "session-abc"
