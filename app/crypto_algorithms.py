"""Cryptographic and classical cipher helpers for the desktop app."""

from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class CryptoError(Exception):
    """Base error for crypto operations."""


class NonReversibleAlgorithmError(CryptoError):
    """Raised when trying to decrypt a one-way algorithm."""


class InvalidKeyError(CryptoError):
    """Raised when key is invalid or missing."""


class InvalidCipherTextError(CryptoError):
    """Raised when ciphertext is malformed or cannot be decrypted."""


@dataclass(frozen=True)
class AlgorithmDescription:
    name: str
    purpose: str
    security: str


ALGORITHM_DESCRIPTIONS: dict[str, AlgorithmDescription] = {
    "Caesar": AlgorithmDescription(
        name="Caesar",
        purpose="教学与入门演示：用固定偏移量替换字母。",
        security="极弱，不可用于真实安全场景。",
    ),
    "Rail Fence": AlgorithmDescription(
        name="Rail Fence",
        purpose="教学与古典密码演示：按栅栏轨道重排字符。",
        security="极弱，不可用于真实安全场景。",
    ),
    "MD5": AlgorithmDescription(
        name="MD5",
        purpose="摘要指纹：常用于校验完整性。",
        security="已不安全，不建议用于密码存储或安全签名。",
    ),
    "SHA-256": AlgorithmDescription(
        name="SHA-256",
        purpose="摘要指纹：完整性校验与签名前处理常见。",
        security="当前仍安全，但摘要本身不可逆。密码存储应使用专用 KDF/哈希方案。",
    ),
    "AES": AlgorithmDescription(
        name="AES-GCM",
        purpose="对称加密：保护敏感文本的机密性和完整性。",
        security="强，需保管好口令/密钥。使用随机盐和随机 nonce。",
    ),
}


def _shift_alpha(ch: str, shift: int) -> str:
    if not ch.isalpha():
        return ch

    base = ord("A") if ch.isupper() else ord("a")
    return chr((ord(ch) - base + shift) % 26 + base)


def caesar_encrypt(text: str, shift: int) -> str:
    return "".join(_shift_alpha(ch, shift) for ch in text)


def caesar_decrypt(text: str, shift: int) -> str:
    return caesar_encrypt(text, -shift)


def rail_fence_encrypt(text: str, rails: int) -> str:
    if rails < 2:
        raise InvalidKeyError("栅栏加密的轨道数必须 >= 2")

    fences = ["" for _ in range(rails)]
    rail = 0
    direction = 1

    for ch in text:
        fences[rail] += ch
        rail += direction
        if rail == 0 or rail == rails - 1:
            direction *= -1

    return "".join(fences)


def rail_fence_decrypt(ciphertext: str, rails: int) -> str:
    if rails < 2:
        raise InvalidKeyError("栅栏解密的轨道数必须 >= 2")
    if not ciphertext:
        return ""

    pattern = []
    rail = 0
    direction = 1
    for _ in ciphertext:
        pattern.append(rail)
        rail += direction
        if rail == 0 or rail == rails - 1:
            direction *= -1

    counts = [pattern.count(r) for r in range(rails)]

    rails_data: list[list[str]] = []
    idx = 0
    for count in counts:
        rails_data.append(list(ciphertext[idx : idx + count]))
        idx += count

    pointers = [0] * rails
    plain = []
    for r in pattern:
        plain.append(rails_data[r][pointers[r]])
        pointers[r] += 1

    return "".join(plain)


def md5_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def sha256_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    if not passphrase:
        raise InvalidKeyError("AES 需要非空口令")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def aes_encrypt(plaintext: str, passphrase: str) -> str:
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

    payload = b"v1" + salt + nonce + ciphertext
    return base64.urlsafe_b64encode(payload).decode("ascii")


def aes_decrypt(token: str, passphrase: str) -> str:
    if not token:
        raise InvalidCipherTextError("请输入待解密内容")

    try:
        payload = base64.urlsafe_b64decode(token.encode("ascii"))
    except Exception as exc:  # noqa: BLE001
        raise InvalidCipherTextError("AES 密文格式无效") from exc

    if len(payload) < 2 + 16 + 12 + 16:
        raise InvalidCipherTextError("AES 密文长度异常")

    version = payload[:2]
    if version != b"v1":
        raise InvalidCipherTextError("不支持的密文版本")

    salt = payload[2:18]
    nonce = payload[18:30]
    ciphertext = payload[30:]

    key = _derive_key(passphrase, salt)
    aesgcm = AESGCM(key)

    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as exc:  # noqa: BLE001
        raise InvalidCipherTextError("AES 解密失败，请检查口令或密文") from exc

    return plaintext.decode("utf-8")


def process_text(algorithm: str, mode: str, text: str, key: str) -> str:
    algo = algorithm.strip()
    op = mode.lower().strip()

    if algo == "Caesar":
        try:
            shift = int(key)
        except ValueError as exc:
            raise InvalidKeyError("凯撒密钥需为整数偏移量") from exc

        return caesar_encrypt(text, shift) if op == "encrypt" else caesar_decrypt(text, shift)

    if algo == "Rail Fence":
        try:
            rails = int(key)
        except ValueError as exc:
            raise InvalidKeyError("栅栏密钥需为整数轨道数") from exc

        return rail_fence_encrypt(text, rails) if op == "encrypt" else rail_fence_decrypt(text, rails)

    if algo == "MD5":
        if op == "decrypt":
            raise NonReversibleAlgorithmError("MD5 是不可逆摘要算法，无法解密")
        return md5_hash(text)

    if algo == "SHA-256":
        if op == "decrypt":
            raise NonReversibleAlgorithmError("SHA-256 是不可逆摘要算法，无法解密")
        return sha256_hash(text)

    if algo == "AES":
        return aes_encrypt(text, key) if op == "encrypt" else aes_decrypt(text, key)

    raise CryptoError(f"不支持的算法：{algorithm}")
