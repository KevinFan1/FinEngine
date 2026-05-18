"""Login captcha generation and verification."""

from __future__ import annotations

import base64
import secrets
import time
import uuid
from dataclasses import dataclass

import redis.asyncio as redis

from app.core.config import settings


CAPTCHA_ALPHABET = "23456789"
CAPTCHA_KEY_PREFIX = "finengine:captcha:"
SEGMENTS: dict[str, tuple[str, ...]] = {
    "0": ("a", "b", "c", "d", "e", "f"),
    "1": ("b", "c"),
    "2": ("a", "b", "g", "e", "d"),
    "3": ("a", "b", "g", "c", "d"),
    "4": ("f", "g", "b", "c"),
    "5": ("a", "f", "g", "c", "d"),
    "6": ("a", "f", "e", "d", "c", "g"),
    "7": ("a", "b", "c"),
    "8": ("a", "b", "c", "d", "e", "f", "g"),
    "9": ("a", "b", "c", "d", "f", "g"),
}


@dataclass(frozen=True)
class CaptchaChallenge:
    captcha_id: str
    image: str
    expires_in: int


class CaptchaService:
    def __init__(self, *, ttl_seconds: int = 300, max_memory_store: int = 1000) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_memory_store = max_memory_store
        self._store: dict[str, tuple[str, float]] = {}
        self._redis: redis.Redis | None = None

    async def generate(self) -> CaptchaChallenge:
        self._cleanup()

        # Prevent memory leak: limit in-memory store size
        if len(self._store) >= self.max_memory_store:
            from loguru import logger
            logger.warning(f"Memory captcha store full ({self.max_memory_store}), clearing old entries")
            # Keep only the most recent entries
            sorted_items = sorted(self._store.items(), key=lambda x: x[1][1], reverse=True)
            self._store = dict(sorted_items[:self.max_memory_store // 2])

        captcha_id = uuid.uuid4().hex
        code = "".join(secrets.choice(CAPTCHA_ALPHABET) for _ in range(4))
        if not await self._save_to_redis(captcha_id, code):
            self._store[captcha_id] = (code, time.time() + self.ttl_seconds)
        return CaptchaChallenge(
            captcha_id=captcha_id,
            image=_svg_data_url(code),
            expires_in=self.ttl_seconds,
        )

    async def verify(self, captcha_id: str | None, code: str | None) -> bool:
        self._cleanup()
        if not captcha_id or not code:
            return False

        redis_code = await self._pop_from_redis(captcha_id)
        if redis_code is not None:
            return redis_code.upper() == code.strip().upper()

        stored = self._store.pop(captcha_id, None)
        if stored is None:
            return False

        expected, expires_at = stored
        if expires_at < time.time():
            return False
        return expected.upper() == code.strip().upper()

    def _cleanup(self) -> None:
        now = time.time()
        expired = [key for key, (_, expires_at) in self._store.items() if expires_at < now]
        for key in expired:
            self._store.pop(key, None)

    async def _save_to_redis(self, captcha_id: str, code: str) -> bool:
        try:
            client = self._redis_client()
            await client.setex(f"{CAPTCHA_KEY_PREFIX}{captcha_id}", self.ttl_seconds, code)
            return True
        except Exception:
            return False

    async def _pop_from_redis(self, captcha_id: str) -> str | None:
        try:
            client = self._redis_client()
            key = f"{CAPTCHA_KEY_PREFIX}{captcha_id}"
            async with client.pipeline(transaction=True) as pipe:
                pipe.get(key)
                pipe.delete(key)
                value, _ = await pipe.execute()
            if isinstance(value, bytes):
                return value.decode("utf-8")
            return value
        except Exception:
            return None

    def _redis_client(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis


def _svg_data_url(code: str) -> str:
    lines = "\n".join(
        f'<line x1="{secrets.randbelow(130)}" y1="{secrets.randbelow(44)}" '
        f'x2="{secrets.randbelow(130)}" y2="{secrets.randbelow(44)}" '
        f'stroke="rgba({80 + secrets.randbelow(80)},{90 + secrets.randbelow(80)},{110 + secrets.randbelow(80)},0.34)" '
        f'stroke-width="{1 + secrets.randbelow(2)}"/>'
        for _ in range(14)
    )
    curves = "\n".join(
        f'<path d="M {secrets.randbelow(30)} {secrets.randbelow(44)} '
        f'C {30 + secrets.randbelow(30)} {secrets.randbelow(44)}, '
        f'{70 + secrets.randbelow(30)} {secrets.randbelow(44)}, '
        f'{100 + secrets.randbelow(30)} {secrets.randbelow(44)}" '
        f'fill="none" stroke="rgba(23,59,104,0.28)" stroke-width="{1 + secrets.randbelow(2)}"/>'
        for _ in range(4)
    )
    grid = "\n".join(
        [
            *(
                f'<line x1="{x}" y1="0" x2="{x + secrets.choice((-3, 3))}" y2="44" '
                'stroke="rgba(23,59,104,0.08)" stroke-width="1"/>'
                for x in range(10, 130, 16)
            ),
            *(
                f'<line x1="0" y1="{y}" x2="130" y2="{y + secrets.choice((-2, 2))}" '
                'stroke="rgba(23,59,104,0.07)" stroke-width="1"/>'
                for y in range(8, 44, 10)
            ),
        ]
    )
    dots = "\n".join(
        f'<circle cx="{secrets.randbelow(130)}" cy="{secrets.randbelow(44)}" '
        f'r="{1 + secrets.randbelow(2)}" fill="rgba(23,59,104,0.{18 + secrets.randbelow(35)})"/>'
        for _ in range(70)
    )
    masks = "\n".join(
        f'<rect x="{16 + index * 24 + secrets.randbelow(8)}" y="{8 + secrets.randbelow(18)}" '
        f'width="{8 + secrets.randbelow(8)}" height="{3 + secrets.randbelow(4)}" '
        'fill="rgba(244,248,251,0.58)"/>'
        for index in range(len(code))
    )
    digits = "\n".join(_digit_svg(char, 20 + index * 24, 9) for index, char in enumerate(code))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="130" height="44" viewBox="0 0 130 44">
  <rect width="130" height="44" rx="6" fill="#f4f8fb"/>
  {grid}
  {lines}
  {dots}
  {digits}
  {curves}
  {masks}
</svg>"""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _digit_svg(char: str, x: int, y: int) -> str:
    x += secrets.choice((-2, -1, 0, 1, 2))
    y += secrets.choice((-2, -1, 0, 1, 2))
    points = {
        "a": (x + 3, y, x + 15, y),
        "b": (x + 18, y + 3, x + 18, y + 13),
        "c": (x + 18, y + 17, x + 18, y + 27),
        "d": (x + 3, y + 30, x + 15, y + 30),
        "e": (x, y + 17, x, y + 27),
        "f": (x, y + 3, x, y + 13),
        "g": (x + 3, y + 15, x + 15, y + 15),
    }
    rotate = secrets.choice((-9, -6, -3, 0, 3, 6, 9))
    lines = [
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="#173b68" stroke-width="{3 + secrets.randbelow(2)}" stroke-linecap="round"/>'
        for segment, (x1, y1, x2, y2) in points.items()
        if segment in SEGMENTS[char]
    ]
    return f'<g opacity="0.88" transform="rotate({rotate} {x + 9} {y + 15})">{"".join(lines)}</g>'


captcha_service = CaptchaService()
