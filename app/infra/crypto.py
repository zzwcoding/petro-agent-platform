"""infra.crypto —— SM3/SM4 国密算法唯一出口（ADR-0003 裁决 6）。

- SM4：字段级列加密——`EncryptedField`（infra.db）的 crypto 回调供给方
  （99 册 §4.2「真实加解密由 infra.crypto 注入」）。CBC 模式＋随机 IV 前置、
  密文 base64：同一明文两次加密密文不同（免频度分析），IV 随密文自载。
- SM3：摘要（audit_log.digest / api_key.fingerprint——99 §2.1，应用层计算、
  不依赖 DB 函数——99 §1.7.3 跨库一致）。
- 密钥不落码：经 infra.config Settings.sm4_key（hex 32 位＝16 字节）注入，
  生产由部署环境覆盖；本模块只依赖 gmssl 与 stdlib——不咬上层（B16/B1）。
"""

from __future__ import annotations

import base64
import os

from gmssl import sm3
from gmssl.sm4 import SM4_DECRYPT, SM4_ENCRYPT, CryptSM4

from app.infra.db import EncryptedField

SM4_KEY_BYTES = 16
_SM4_BLOCK = 16

KeyLike = bytes | str | bytearray


def parse_key(key: KeyLike) -> bytes:
    """归一 SM4 密钥：hex 串解码或原样字节；非 16 字节即拒（显式失败不静默）。"""
    raw = bytes.fromhex(key) if isinstance(key, str) else bytes(key)
    if len(raw) != SM4_KEY_BYTES:
        raise ValueError(f"SM4 密钥须为 {SM4_KEY_BYTES} 字节（hex 32 位），当前 {len(raw)} 字节")
    return raw


def sm4_encrypt(plaintext: str, key: KeyLike) -> str:
    """SM4-CBC 加密：随机 IV 前置＋密文，整体 base64（ASCII 安全落 Text 列）。"""
    iv = os.urandom(_SM4_BLOCK)
    crypt = CryptSM4()
    crypt.set_key(parse_key(key), SM4_ENCRYPT)
    body = crypt.crypt_cbc(iv, plaintext.encode("utf-8"))
    return base64.b64encode(iv + body).decode("ascii")


def sm4_decrypt(ciphertext: str, key: KeyLike) -> str:
    """SM4-CBC 解密（sm4_encrypt 的严格逆）。"""
    blob = base64.b64decode(ciphertext.encode("ascii"))
    if len(blob) < _SM4_BLOCK * 2 or (len(blob) - _SM4_BLOCK) % _SM4_BLOCK != 0:
        raise ValueError("SM4 密文形状非法（IV+整块密文）")
    crypt = CryptSM4()
    crypt.set_key(parse_key(key), SM4_DECRYPT)
    plain = crypt.crypt_cbc(blob[:_SM4_BLOCK], blob[_SM4_BLOCK:])
    plain_text: str = plain.decode("utf-8")
    return plain_text


def sm3_digest(text: str) -> str:
    """SM3 摘要（hex 64 位）——审计 digest/凭证指纹的计算底座。"""
    digest: str = sm3.sm3_hash(list(text.encode("utf-8")))
    return digest


def sm4_encrypted_field(key: KeyLike) -> EncryptedField:
    """装配 SM4 加密列类型：`EncryptedField`（seam）× 本模块实现（回调注入）。"""
    return EncryptedField(
        encrypt=lambda s: sm4_encrypt(s, key),
        decrypt=lambda s: sm4_decrypt(s, key),
    )
