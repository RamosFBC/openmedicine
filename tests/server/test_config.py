import pytest


class TestServiceConfig:
    def test_defaults(self):
        from open_medicine.server.config import ServiceConfig
        config = ServiceConfig()
        assert config.auth_mode == "none"
        assert config.port == 8000
        assert config.host == "0.0.0.0"

    def test_auth_mode_api_key(self, monkeypatch):
        from open_medicine.server.config import ServiceConfig
        monkeypatch.setenv("OM_AUTH_MODE", "api_key")
        monkeypatch.setenv("OM_API_KEYS", "key1,key2")
        config = ServiceConfig()
        assert config.auth_mode == "api_key"
        assert config.valid_api_keys == {"key1", "key2"}

    def test_invalid_auth_mode_rejected(self, monkeypatch):
        from open_medicine.server.config import ServiceConfig
        monkeypatch.setenv("OM_AUTH_MODE", "invalid")
        with pytest.raises(Exception):
            ServiceConfig()
