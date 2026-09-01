import base64
import hashlib
from cryptography.fernet import Fernet
from app.config import settings

def _get_fernet() -> Fernet:
    # 依據 settings.ENCRYPTION_KEY 衍生 32-byte urlsafe base64 金鑰
    key_bytes = hashlib.sha256(settings.ENCRYPTION_KEY.encode('utf-8')).digest()
    urlsafe_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(urlsafe_key)

def encrypt_data(plain_text: str) -> str:
    """加密明文字串並回傳 base64 字串"""
    if not plain_text:
        return ""
    f = _get_fernet()
    return f.encrypt(plain_text.encode('utf-8')).decode('utf-8')

def decrypt_data(cipher_text: str) -> str:
    """解密 cipher_text 並回傳原始字串"""
    if not cipher_text:
        return ""
    f = _get_fernet()
    try:
        return f.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
    except Exception as e:
        raise ValueError(f"解密失敗: {e}")
