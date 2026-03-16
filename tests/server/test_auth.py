import asyncio
import pytest


class TestApiKeyVerifier:
    def test_valid_key_returns_access_token(self):
        from open_medicine.server.auth import ApiKeyVerifier
        verifier = ApiKeyVerifier(valid_keys={"test-key-1", "test-key-2"})
        result = asyncio.get_event_loop().run_until_complete(
            verifier.verify_token("test-key-1")
        )
        assert result is not None
        assert result.client_id == "api_key_client"
        assert result.token == "test-key-1"

    def test_invalid_key_returns_none(self):
        from open_medicine.server.auth import ApiKeyVerifier
        verifier = ApiKeyVerifier(valid_keys={"test-key-1"})
        result = asyncio.get_event_loop().run_until_complete(
            verifier.verify_token("wrong-key")
        )
        assert result is None

    def test_empty_key_returns_none(self):
        from open_medicine.server.auth import ApiKeyVerifier
        verifier = ApiKeyVerifier(valid_keys={"test-key-1"})
        result = asyncio.get_event_loop().run_until_complete(
            verifier.verify_token("")
        )
        assert result is None


class TestCreateVerifier:
    def test_none_mode_returns_none(self):
        from open_medicine.server.auth import create_verifier
        from open_medicine.server.config import ServiceConfig
        config = ServiceConfig(auth_mode="none")
        assert create_verifier(config) is None

    def test_api_key_mode_returns_verifier(self):
        from open_medicine.server.auth import create_verifier, ApiKeyVerifier
        from open_medicine.server.config import ServiceConfig
        config = ServiceConfig(auth_mode="api_key", api_keys="k1,k2")
        verifier = create_verifier(config)
        assert isinstance(verifier, ApiKeyVerifier)
