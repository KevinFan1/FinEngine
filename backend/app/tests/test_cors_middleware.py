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
