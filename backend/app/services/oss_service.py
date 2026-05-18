"""Alibaba Cloud OSS file service — object streaming and STS tokens."""

import base64
import hashlib
import hmac
import urllib.parse
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import oss2

from app.core.config import settings


class AliyunOSSService:
    """Stream files from Alibaba Cloud OSS."""

    def _require_config(self) -> None:
        missing = [
            name
            for name, value in (
                ("ALIYUN_ACCESS_KEY_ID", settings.ALIYUN_ACCESS_KEY_ID),
                ("ALIYUN_ACCESS_KEY_SECRET", settings.ALIYUN_ACCESS_KEY_SECRET),
                ("ALIYUN_OSS_BUCKET", settings.ALIYUN_OSS_BUCKET),
                ("ALIYUN_OSS_ENDPOINT", settings.ALIYUN_OSS_ENDPOINT),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"阿里云 OSS 配置缺失: {', '.join(missing)}")

    @staticmethod
    def normalized_endpoint(*, internal: bool = False) -> str:
        """Return a region endpoint suitable for OSS SDK bucket clients."""
        internal_endpoint = settings.ALIYUN_OSS_INTERNAL_ENDPOINT.strip()
        endpoint = (internal_endpoint if internal and internal_endpoint else settings.ALIYUN_OSS_ENDPOINT).rstrip("/")
        parsed = urllib.parse.urlparse(endpoint)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("ALIYUN_OSS_ENDPOINT 必须包含协议和域名，例如 https://oss-cn-guangzhou.aliyuncs.com")

        bucket_prefix = f"{settings.ALIYUN_OSS_BUCKET}."
        host = parsed.netloc
        if host.startswith(bucket_prefix):
            host = host[len(bucket_prefix) :]
        if internal and not internal_endpoint:
            host = _internal_oss_host(host)
        return f"{parsed.scheme}://{host}"

    def _bucket(self, *, internal: bool = False) -> oss2.Bucket:
        self._require_config()
        auth = oss2.Auth(settings.ALIYUN_ACCESS_KEY_ID, settings.ALIYUN_ACCESS_KEY_SECRET)
        return oss2.Bucket(auth, self.normalized_endpoint(internal=internal), settings.ALIYUN_OSS_BUCKET)

    def download_to_temp(
        self,
        oss_key: str,
        local_path: str,
        *,
        chunk_size: int = 1024 * 1024,
        max_size: int = 1024 * 1024 * 1024,  # 1GB default limit
    ):
        """Stream an OSS object to a local temp path for processing.

        Args:
            oss_key: OSS object key
            local_path: Local file path to save
            chunk_size: Download chunk size in bytes
            max_size: Maximum file size in bytes (default 1GB)

        Raises:
            ValueError: If file size exceeds max_size
        """
        result = self._bucket(internal=settings.INTERNAL_DOWNLOAD).get_object(oss_key)

        # Check content length if available
        content_length = result.content_length
        if content_length and content_length > max_size:
            raise ValueError(f"文件过大: {content_length} bytes (最大 {max_size} bytes)")

        downloaded = 0
        with Path(local_path).open("wb") as f:
            while True:
                chunk = result.read(chunk_size)
                if not chunk:
                    break
                downloaded += len(chunk)
                if downloaded > max_size:
                    # Clean up partial file
                    Path(local_path).unlink(missing_ok=True)
                    raise ValueError(f"下载超过大小限制: {max_size} bytes")
                f.write(chunk)


# ── Alibaba Cloud OSS STS ────────────────────────────────────────────────────

_STS_ENDPOINT = "https://sts.aliyuncs.com"


def _sign_sts_params(params: dict, access_key_secret: str) -> str:
    """Sign parameters using Alibaba Cloud ACS1 signature mechanism."""
    sorted_params = sorted(params.items())
    encoded_parts = [f"{urllib.parse.quote(str(k), safe='')}={urllib.parse.quote(str(v), safe='')}" for k, v in sorted_params]
    canonical_query = "&".join(encoded_parts)
    string_to_sign = f"POST&%2F&{urllib.parse.quote(canonical_query, safe='')}"
    signing_key = access_key_secret + "&"
    signature = base64.b64encode(
        hmac.new(
            signing_key.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    ).decode("utf-8")
    return signature


def assume_sts_role(
    role_arn: str,
    session_name: str,
    duration_seconds: int = 3600,
    policy: str | None = None,
) -> dict:
    """Call Alibaba Cloud STS AssumeRole API and return temporary credentials.

    Returns dict with keys:
      access_key_id, access_key_secret, security_token, expiration
    """
    params: dict[str, str] = {
        "Action": "AssumeRole",
        "Version": "2015-04-01",
        "Format": "JSON",
        "RoleArn": role_arn,
        "RoleSessionName": session_name,
        "DurationSeconds": str(duration_seconds),
        "AccessKeyId": settings.ALIYUN_ACCESS_KEY_ID,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureVersion": "1.0",
        "SignatureNonce": str(uuid.uuid4()),
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if policy:
        params["Policy"] = policy

    params["Signature"] = _sign_sts_params(params, settings.ALIYUN_ACCESS_KEY_SECRET)

    resp = httpx.post(_STS_ENDPOINT, data=params, timeout=10)
    resp.raise_for_status()
    body = resp.json()

    if "Credentials" not in body:
        raise ValueError(f"STS AssumeRole failed: {body}")

    creds = body["Credentials"]
    return {
        "access_key_id": creds["AccessKeyId"],
        "access_key_secret": creds["AccessKeySecret"],
        "security_token": creds["SecurityToken"],
        "expiration": creds["Expiration"],
    }


# Singletons
oss_service = AliyunOSSService()


def _internal_oss_host(host: str) -> str:
    if "-internal." in host:
        return host
    if ".aliyuncs.com" not in host:
        return host
    prefix, suffix = host.split(".aliyuncs.com", maxsplit=1)
    return f"{prefix}-internal.aliyuncs.com{suffix}"
