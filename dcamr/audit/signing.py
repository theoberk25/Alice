"""Replaceable checkpoint signing and externally configured verification."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class SigningError(RuntimeError):
    """A checkpoint could not be signed."""


class TrustError(RuntimeError):
    """A signature could not be verified by configured trust."""


class Signer(Protocol):
    """Interface supplied to the ledger for checkpoint signing."""

    algorithm_id: str
    key_id: str

    def sign(self, message: bytes) -> bytes:
        """Return a signature over ``message``."""


class _Verifier(Protocol):
    def verify(self, signature: bytes, message: bytes) -> None:
        """Raise when ``signature`` does not authenticate ``message``."""


class TrustStore:
    """Fixed registry of verifiers selected by exact algorithm and key IDs."""

    def __init__(
        self, verifiers: Mapping[tuple[str, str], _Verifier]
    ) -> None:
        try:
            configured = dict(verifiers)
        except Exception:
            raise TrustError("invalid trust configuration") from None

        try:
            for identity, verifier in configured.items():
                if (
                    not isinstance(identity, tuple)
                    or len(identity) != 2
                    or not all(
                        isinstance(value, str) and value for value in identity
                    )
                    or not callable(getattr(verifier, "verify", None))
                ):
                    raise TrustError("invalid trust configuration")
        except TrustError:
            raise
        except Exception:
            raise TrustError("invalid trust configuration") from None
        self._verifiers = configured

    def verify(
        self,
        algorithm_id: str,
        key_id: str,
        message: bytes,
        signature: bytes,
    ) -> None:
        if not isinstance(algorithm_id, str) or not isinstance(key_id, str):
            raise TrustError("invalid signing identity")
        verifier = self._verifiers.get((algorithm_id, key_id))
        if verifier is None:
            raise TrustError("untrusted signing identity")
        if not isinstance(message, bytes) or not isinstance(signature, bytes):
            raise TrustError("signature verification failed")
        try:
            verifier.verify(signature, message)
        except Exception:
            raise TrustError("signature verification failed") from None


class Ed25519Signer:
    """Ed25519 signer initialized from a 32-byte private key seed."""

    algorithm_id = "ed25519"

    def __init__(self, private_key_bytes: bytes, key_id: str) -> None:
        if not isinstance(private_key_bytes, bytes):
            raise SigningError("invalid Ed25519 private key")
        if not isinstance(key_id, str) or not key_id:
            raise SigningError("invalid signing key identity")
        try:
            self._private_key = Ed25519PrivateKey.from_private_bytes(
                private_key_bytes
            )
        except Exception:
            raise SigningError("invalid Ed25519 private key") from None
        self.key_id = key_id

    def sign(self, message: bytes) -> bytes:
        if not isinstance(message, bytes):
            raise SigningError("checkpoint message must be bytes")
        try:
            return self._private_key.sign(message)
        except Exception:
            raise SigningError("Ed25519 signing failed") from None


class Ed25519Verifier:
    """Ed25519 verifier initialized from a 32-byte public key."""

    def __init__(self, public_key_bytes: bytes) -> None:
        if not isinstance(public_key_bytes, bytes):
            raise TrustError("invalid Ed25519 public key")
        try:
            self._public_key = Ed25519PublicKey.from_public_bytes(
                public_key_bytes
            )
        except Exception:
            raise TrustError("invalid Ed25519 public key") from None

    def verify(self, signature: bytes, message: bytes) -> None:
        if not isinstance(signature, bytes) or not isinstance(message, bytes):
            raise TrustError("signature verification failed")
        try:
            self._public_key.verify(signature, message)
        except Exception:
            raise TrustError("signature verification failed") from None
