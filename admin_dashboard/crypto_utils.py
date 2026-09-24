import os
from cryptography.fernet import Fernet, InvalidToken


def _get_fernet():
    key = os.environ.get("OTP_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "OTP_ENCRYPTION_KEY environment variable is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
            "and set it as an environment variable before saving or reading the email provider's App Password."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(plain_text):
    if not plain_text:
        return ""
    f = _get_fernet()
    return f.encrypt(plain_text.encode()).decode()


def decrypt_value(encrypted_text):
    if not encrypted_text:
        return ""
    f = _get_fernet()
    try:
        return f.decrypt(encrypted_text.encode()).decode()
    except InvalidToken:
        return ""