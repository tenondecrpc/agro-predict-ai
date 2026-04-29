from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from backend.integrations.oracle_apex.credentials import (
    EnvironmentCredentialResolver,
    VaultCredentialResolver,
    make_credential_resolver,
)


class TestEnvironmentCredentialResolver:
    """Test environment-based credential resolution."""

    def test_resolves_sql_credentials(self) -> None:
        resolver = EnvironmentCredentialResolver()

        with patch.dict(
            os.environ,
            {
                "APEX_CREDS_USER": "oracle_user",
                "APEX_CREDS_PASSWORD": "oracle_pass",
                "APEX_CREDS_DSN": "localhost:1521/XE",
            },
            clear=False,
        ):
            result = resolver.resolve("vault://apex/creds")

            assert result["user"] == "oracle_user"
            assert result["password"] == "oracle_pass"
            assert result["dsn"] == "localhost:1521/XE"

    def test_resolves_rest_credentials(self) -> None:
        resolver = EnvironmentCredentialResolver()

        with patch.dict(
            os.environ,
            {
                "APEX_CREDS_USER": "ords_user",
                "APEX_CREDS_PASSWORD": "ords_pass",
                "APEX_CREDS_BASE_URL": "https://apex.example.com/ords",
            },
            clear=False,
        ):
            result = resolver.resolve("vault://apex/creds")

            assert result["user"] == "ords_user"
            assert result["password"] == "ords_pass"
            assert result["base_url"] == "https://apex.example.com/ords"

    def test_raises_when_missing_credentials(self) -> None:
        resolver = EnvironmentCredentialResolver()

        # Ensure the env vars are not set
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Credentials not found"):
                resolver.resolve("vault://apex/creds")

    def test_raises_when_missing_password(self) -> None:
        resolver = EnvironmentCredentialResolver()

        with patch.dict(
            os.environ,
            {"APEX_CREDS_USER": "oracle_user"},
            clear=False,
        ):
            with pytest.raises(ValueError, match="Credentials not found"):
                resolver.resolve("vault://apex/creds")

    def test_custom_prefix(self) -> None:
        resolver = EnvironmentCredentialResolver()

        with patch.dict(
            os.environ,
            {
                "MY_ORACLE_USER": "custom_user",
                "MY_ORACLE_PASSWORD": "custom_pass",
            },
            clear=False,
        ):
            result = resolver.resolve("vault://my/oracle")

            assert result["user"] == "custom_user"
            assert result["password"] == "custom_pass"


class TestVaultCredentialResolver:
    """Test Vault-based credential resolution (stub)."""

    def test_raises_not_implemented(self) -> None:
        resolver = VaultCredentialResolver()

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            resolver.resolve("vault://apex/creds")

    def test_strips_vault_prefix(self) -> None:
        resolver = VaultCredentialResolver()

        with pytest.raises(NotImplementedError):
            resolver.resolve("secret/data/apex/creds")


class TestMakeCredentialResolver:
    """Test factory function for credential resolvers."""

    def test_returns_env_resolver_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            resolver = make_credential_resolver()
            assert isinstance(resolver, EnvironmentCredentialResolver)

    def test_returns_vault_resolver_when_vault_addr_set(self) -> None:
        with patch.dict(os.environ, {"VAULT_ADDR": "https://vault.example.com"}):
            resolver = make_credential_resolver()
            assert isinstance(resolver, VaultCredentialResolver)
