from starlette.testclient import TestClient

from app.main import app


def test_crypto_error_response_includes_cors_headers() -> None:
    client = TestClient(app)
    origin = "http://127.0.0.1:3000"

    response = client.post(
        "/api/v1/organizations",
        headers={
            "Origin": origin,
            "Authorization": "Bearer invalid-token",
            "Content-Type": "application/json",
            "X-API-Encrypted": "1",
            "X-API-Crypto-Key": "invalid-key",
            "X-API-Timestamp": "invalid-timestamp",
            "X-API-Nonce": "invalid-nonce",
        },
        json={"encrypted": True, "iv": "invalid-iv", "data": "invalid-data"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "请求加密数据解密失败"
    assert response.headers["access-control-allow-origin"] in {origin, "*"}


def test_plain_api_request_is_rejected_when_crypto_enabled() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/platforms")

    assert response.status_code == 200
    assert response.json()["code"] == 400
    assert response.json()["message"] == "接口必须使用加密请求"


def test_api_health_check_does_not_require_crypto() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["code"] == 200
