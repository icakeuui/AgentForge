from __future__ import annotations

import base64
import hashlib
import hmac
import secrets


class PasswordService:
    PBKDF2_ITERATIONS = 390_000
    SALT_BYTES = 16
    HASH_NAME = "sha256"

    def hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(self.SALT_BYTES)
        digest = hashlib.pbkdf2_hmac(
            self.HASH_NAME,
            password.encode("utf-8"),
            salt,
            self.PBKDF2_ITERATIONS,
        )
        encoded_salt = base64.urlsafe_b64encode(salt).decode("utf-8").rstrip("=")
        encoded_hash = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
        return f"pbkdf2_sha256${self.PBKDF2_ITERATIONS}${encoded_salt}${encoded_hash}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            scheme, iterations_raw, encoded_salt, encoded_hash = password_hash.split("$", 3)
            if scheme != "pbkdf2_sha256":
                return False
            iterations = int(iterations_raw)
            salt = base64.urlsafe_b64decode(self._pad_base64(encoded_salt))
            expected = base64.urlsafe_b64decode(self._pad_base64(encoded_hash))
        except Exception:
            return False

        digest = hashlib.pbkdf2_hmac(
            self.HASH_NAME,
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(digest, expected)

    def validate_strength(self, password: str) -> None:
        return None

    @staticmethod
    def _pad_base64(value: str) -> str:
        remainder = len(value) % 4
        if remainder == 0:
            return value
        return value + "=" * (4 - remainder)


password_service = PasswordService()
