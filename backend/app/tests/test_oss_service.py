from app.services.oss_service import AliyunOSSService


def test_sign_download_url_sets_attachment_filename(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeBucket:
        def sign_url(self, method, key, expires, headers=None, params=None, slash_safe=False, additional_headers=None):
            captured.update(
                {
                    "method": method,
                    "key": key,
                    "expires": expires,
                    "headers": headers,
                    "params": params,
                    "slash_safe": slash_safe,
                    "additional_headers": additional_headers,
                }
            )
            return "https://oss.test/download"

    service = AliyunOSSService()
    monkeypatch.setattr(service, "_require_config", lambda: None)
    monkeypatch.setattr(service, "_bucket", lambda *, internal=False: FakeBucket())

    url = service.sign_download_url(
        "source-key.xlsx",
        expires_seconds=300,
        filename='原"表.xlsx',
    )

    assert url == "https://oss.test/download"
    assert captured["method"] == "GET"
    assert captured["key"] == "source-key.xlsx"
    assert captured["expires"] == 300
    assert captured["params"] == {
        "response-content-disposition": "attachment; filename=\"原\\\"表.xlsx\"; filename*=UTF-8''%E5%8E%9F%22%E8%A1%A8.xlsx",
    }
