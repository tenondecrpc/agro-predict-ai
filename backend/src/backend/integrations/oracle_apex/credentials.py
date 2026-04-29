"""Credential resolver for Oracle APEX connections.

Resolves credential references (e.g., vault://apex/creds) to actual
credentials. In production this integrates with HashiCorp Vault or
Kubernetes External Secrets Operator. For development, a simple
environment-based resolver is provided.
"""

from __future__ import annotations

import logging
import os
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class CredentialResolver(Protocol):
    """Protocol for resolving credential references to actual secrets."""

    def resolve(self, credentials_ref: str) -> dict[str, str]: ...


class EnvironmentCredentialResolver:
    """Resolve credentials from environment variables.

    Maps a reference like 'vault://apex/creds' to environment variables:
    - APEX_CREDS_USER  -> user
    - APEX_CREDS_PASSWORD -> password
    - APEX_CREDS_DSN   -> dsn (for SQL adapter)
    - APEX_CREDS_BASE_URL -> base_url (for REST adapter)
    """

    def resolve(self, credentials_ref: str) -> dict[str, str]:
        """Resolve a credential reference to a dict of secrets.

        Parameters
        ----------
        credentials_ref:
            A reference string like 'vault://apex/creds'. The path portion
            is used as a prefix for environment variable lookup.

        Returns
        -------
        dict[str, str]
            Resolved credentials with keys: user, password, and optionally
            dsn or base_url.

        Raises
        ------
        ValueError:
            If required environment variables are not set.
        """
        # Extract the path from the reference (e.g., 'apex/creds' from 'vault://apex/creds')
        path = credentials_ref
        if "://" in path:
            path = path.split("://", 1)[1]

        # Convert path to env var prefix (e.g., 'apex/creds' -> 'APEX_CREDS')
        prefix = path.replace("/", "_").upper()

        user = os.environ.get(f"{prefix}_USER")
        password = os.environ.get(f"{prefix}_PASSWORD")

        if not user or not password:
            raise ValueError(
                f"Credentials not found for reference '{credentials_ref}'. "
                f"Set {prefix}_USER and {prefix}_PASSWORD environment variables."
            )

        result: dict[str, str] = {"user": user, "password": password}

        dsn = os.environ.get(f"{prefix}_DSN")
        if dsn:
            result["dsn"] = dsn

        base_url = os.environ.get(f"{prefix}_BASE_URL")
        if base_url:
            result["base_url"] = base_url

        return result


class VaultCredentialResolver:
    """Resolve credentials from HashiCorp Vault.

    This is a stub implementation. In production, integrate with the
    actual Vault API or use the hvac library.
    """

    def __init__(
        self,
        *,
        vault_addr: str | None = None,
        vault_token: str | None = None,
    ) -> None:
        self._vault_addr = vault_addr or os.environ.get("VAULT_ADDR", "")
        self._vault_token = vault_token or os.environ.get("VAULT_TOKEN", "")

    def resolve(self, credentials_ref: str) -> dict[str, str]:
        """Resolve a credential reference from Vault.

        Parameters
        ----------
        credentials_ref:
            A Vault path like 'secret/data/apex/creds' or 'vault://apex/creds'.

        Returns
        -------
        dict[str, str]
            Resolved credentials from Vault.

        Raises
        ------
        NotImplementedError:
            Always raised until Vault integration is implemented.
        """
        # Strip vault:// prefix if present
        path = credentials_ref
        if path.startswith("vault://"):
            path = path[len("vault://"):]

        logger.info(
            "vault_credential_resolve_requested",
            extra={"path": path, "vault_addr": self._vault_addr},
        )

        raise NotImplementedError(
            "Vault credential resolution is not yet implemented. "
            "Use EnvironmentCredentialResolver for development, or "
            "implement the Vault API integration."
        )


def make_credential_resolver() -> CredentialResolver:
    """Create the appropriate credential resolver based on environment.

    Returns a VaultCredentialResolver if VAULT_ADDR is set, otherwise
    falls back to EnvironmentCredentialResolver.
    """
    if os.environ.get("VAULT_ADDR"):
        return VaultCredentialResolver()
    return EnvironmentCredentialResolver()
